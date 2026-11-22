#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一认证与会话（§8.6）。

设计红线：**后端永不接收、也不存储学生的学校密码。**
流程只能是：后端 302 到学校登录页 → 学生在那里输学号密码 → 学校带 ticket 跳回 →
后端用 ticket 换取学号 → 建立自己的会话。

两种模式（环境变量 PINE_AUTH_MODE）：
  mock —— 本地开发用。不联网，直接签发一个演示学生。
  cas  —— 学校 CAS 3.0。需要配置三个地址（见 SCHOOL_AUTH.md）。

未配置好之前一律走 mock，并在会话里标 source=mock，前端据此显示「演示登录」。
"""
import json
import os
import re
import secrets
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SESSION_FILE = os.path.join(ROOT, 'var', 'sessions.json')
SESSION_COOKIE = 'pine_session'
SESSION_TTL = 8 * 3600

MODE = os.environ.get('PINE_AUTH_MODE', 'mock')
CAS_LOGIN_URL = os.environ.get('PINE_CAS_LOGIN_URL', '')
CAS_VALIDATE_URL = os.environ.get('PINE_CAS_VALIDATE_URL', '')
APP_BASE_URL = os.environ.get('PINE_APP_BASE_URL', 'http://127.0.0.1:8000')
FRONTEND_URL = os.environ.get('PINE_FRONTEND_URL', 'http://localhost:5173')

# mock 学生：两个不同的人，用来验收「换一个学生结果会变」
MOCK_STUDENTS = {
    'demo_a': {
        'student_id': '2024A001', 'name': '林小满',
        'major': '工科试验班（智能装备）', 'enroll_year': 2024,
    },
    'demo_b': {
        'student_id': '2023B002', 'name': '周予安',
        'major': '工科试验班（智能装备）', 'enroll_year': 2023,
    },
}


class SessionStore:
    """极简会话存储：内存 + var/sessions.json 落盘，重启不算掉。"""

    def __init__(self, path=SESSION_FILE):
        self.path = path
        self.data = {}
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as f:
                self.data = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def create(self, student, source='mock'):
        sid = secrets.token_urlsafe(24)
        self.data[sid] = {
            'student': student,
            'source': source,
            'created_at': int(time.time()),
            'expires_at': int(time.time()) + SESSION_TTL,
        }
        self._save()
        return sid

    def get(self, sid):
        if not sid:
            return None
        s = self.data.get(sid)
        if not s:
            return None
        if s['expires_at'] < time.time():
            self.data.pop(sid, None)
            self._save()
            return None
        return s

    def delete(self, sid):
        if sid and sid in self.data:
            self.data.pop(sid)
            self._save()


store = SessionStore()


def mode():
    return MODE


def is_mock():
    return MODE != 'cas' or not (CAS_LOGIN_URL and CAS_VALIDATE_URL)


def login_url(redirect=None):
    """返回 (跳转地址, 是否需要外部跳转)"""
    redirect = redirect or (FRONTEND_URL + '/#/notebook')
    if is_mock():
        return '/api/v1/auth/callback?code=mock:demo_a&redirect=' + urllib.parse.quote(redirect), False
    service = APP_BASE_URL + '/api/v1/auth/callback'
    url = '%s?service=%s' % (CAS_LOGIN_URL, urllib.parse.quote(service, safe=''))
    return url, True


def _parse_cas_user(xml):
    for tag in ('cas:user', 'user'):
        m = re.search(r'<%s>\s*([^<]+?)\s*</%s>' % (tag, tag), xml)
        if m:
            return m.group(1)
    return None


def exchange(code, service):
    """用学校票据换学生身份。返回 (student_dict, source)"""
    if is_mock():
        sid = code.split(':', 1)[1] if ':' in code else 'demo_a'
        stu = MOCK_STUDENTS.get(sid)
        if not stu:
            raise ValueError('未知的演示学生：%s' % sid)
        return dict(stu), 'mock'

    q = urllib.parse.urlencode({'service': service, 'ticket': code})
    url = CAS_VALIDATE_URL + ('&' if '?' in CAS_VALIDATE_URL else '?') + q
    with urllib.request.urlopen(url, timeout=10) as r:
        xml = r.read().decode('utf-8', 'replace')
    user = _parse_cas_user(xml)
    if not user:
        raise ValueError('CAS 校验失败：未返回学号')
    # 学号到手；姓名/专业等需要教务数据补充，这里只放确定的字段
    return {'student_id': user, 'name': None, 'major': None, 'enroll_year': None}, 'cas'
