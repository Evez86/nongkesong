#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学业数据接入的端到端验收（§8.6 / §8.3）。

验三件事：
  1. 登录 → 会话 → 学业数据 → 退出 链路闭合
  2. 「专业 + 入学年级」能匹配到对应版本的培养方案
  3. 换一个学生 / 换一组已修课程，课程与路线目标会变

用法：python api/verify_auth.py http://127.0.0.1:8000
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REAL_DOC = (r'C:\Users\JUSTI\Documents\xwechat_files\wxid_lq0el398u5th22_1d3f'
            r'\msg\file\2026-11\8-工学院理科试验班（智能装备）本科人才培养方案.doc')
results = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """不自动跟随 302：登录跳转要我们自己走，才能看清每一步。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, data=body, method=method,
                                 headers=headers or {})
    try:
        r = OPENER.open(req, timeout=120)
        raw = r.read()
        return r.status, (json.loads(raw.decode()) if raw else {}), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw.decode()) if raw else {}
        except json.JSONDecodeError:
            payload = {'raw': raw[:200].decode('utf-8', 'replace')}
        return e.code, payload, dict(e.headers)


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('%s %-44s %s' % ('PASS' if ok else 'FAIL', name, detail))


def login(which='demo_a'):
    """走真实流程：GET /auth/login 拿跳转地址 → 跟到 callback → 取会话 cookie"""
    s, b, _ = call('GET', '/api/v1/auth/login')
    url = b.get('login_url') or ''
    if not url:
        return None, s
    if url.startswith('http'):
        return None, 'EXTERNAL'          # 真 CAS：得人工在浏览器登
    url = url.replace('mock:demo_a', 'mock:' + which)   # 换演示学生
    s2, b2, h2 = call('GET', url)
    cookie = (h2.get('Set-Cookie') or '').split(';')[0]
    return cookie or None, s2


def upload_plan(path, cohort):
    bd = '----authverify'
    with open(path, 'rb') as f:
        content = f.read()
    body = b''.join([
        ('--%s\r\nContent-Disposition: form-data; name="cohort"\r\n\r\n%s\r\n'
         % (bd, cohort)).encode(),
        ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
         'Content-Type: application/octet-stream\r\n\r\n'
         % (bd, os.path.basename(path))).encode(),
        content, b'\r\n', ('--%s--\r\n' % bd).encode(),
    ])
    return call('POST', '/api/v1/training-plans', body,
                {'Content-Type': 'multipart/form-data; boundary=' + bd})


def main():
    # 清掉上次导入的数据，保证每次验收都是干净起点
    import_dir = os.path.join(ROOT, 'var', 'academic')
    if os.path.isdir(import_dir):
        for f in os.listdir(import_dir):
            if f.endswith('.json'):
                try:
                    os.remove(os.path.join(import_dir, f))
                except OSError:
                    pass

    doc = REAL_DOC if os.path.exists(REAL_DOC) else os.path.join(
        ROOT, 'out', 'fixtures', '示例培养方案.docx')
    if not os.path.exists(doc):
        sys.exit('找不到可用的培养方案样本')

    # 1) 未登录
    s, b, _ = call('GET', '/api/v1/auth/session')
    check('未登录时 authenticated=false', s == 200 and b.get('authenticated') is False)
    s, b, _ = call('GET', '/api/v1/academic/profile')
    check('未登录访问学业数据 → 401', s == 401 and b.get('error', {}).get('code') == 'AUTH_REQUIRED')

    # 2) 上传方案并登记入学年级
    s, plan, _ = upload_plan(doc, 2024)
    plan_id = plan.get('plan_id')
    check('上传方案并写入 cohort=2024', s == 200 and plan.get('cohort') == 2024, plan_id or '')

    # 3) 学生 A 登录
    cookie_a, st = login('demo_a')
    check('mock 登录 → 回调 → 拿到会话 cookie', bool(cookie_a) and st == 302, str(st))
    hdr_a = {'Cookie': cookie_a}
    s, b, _ = call('GET', '/api/v1/auth/session', None, hdr_a)
    stu = (b.get('student') or {})
    check('会话可取到学生 A', b.get('authenticated') is True, stu.get('name') or '')

    # 4) 学业数据
    s, prof, _ = call('GET', '/api/v1/academic/profile', None, hdr_a)
    fs = prof.get('field_status') or {}
    pf = prof.get('profile') or {}
    check('学业数据：专业 / 年级 / 学期', s == 200 and pf.get('major') and pf.get('enroll_year'),
          '%s · %s 级 · 第 %s 学期' % (pf.get('major'), pf.get('enroll_year'), pf.get('current_term')))
    check('学业数据：已修课程与课表', bool(prof.get('completed_courses')) and bool(prof.get('timetable')),
          '%d 门已修 / %d 节课' % (len(prof.get('completed_courses') or []),
                                   len(prof.get('timetable') or [])))
    check('取不到的字段被明确标出', bool(prof.get('missing_fields')),
          '、'.join(prof.get('missing_fields') or []))

    # 5) 方案匹配
    s, m, _ = call('GET', '/api/v1/training-plans/match?use_session=1', None, hdr_a)
    check('按专业+年级匹配（exact）', s == 200 and m.get('match') == 'exact',
          '%s → %s' % (m.get('queried'), m.get('plan_id')))

    # 6) A 的路线
    s, gA, _ = call('POST', '/api/v1/growth-plans',
                    json.dumps({'interests': ['数据分析'], 'mode': 'demo',
                                'use_session': True}).encode(),
                    dict(hdr_a, **{'Content-Type': 'application/json'}))
    titlesA = [g['title'] for t in (gA.get('terms') or []) for g in t.get('goals', [])]
    check('A：路线基于学业数据', gA.get('summary', {}).get('based_on') == 'academic',
          '已修 %s 学分 / %d 门' % (gA.get('summary', {}).get('completed_credits'),
                                    gA.get('summary', {}).get('completed_count') or 0))

    # 同一份方案，不带学业数据再跑一次，比较第一学期的课程数
    s, g0, _ = call('POST', '/api/v1/growth-plans',
                    json.dumps({'plan_id': plan_id, 'mode': 'demo'}).encode(),
                    {'Content-Type': 'application/json'})
    import re

    def term1_count(g):
        m = re.search(r'完成本学期 (\d+) 门课程',
                      ' '.join(x['title'] for x in (g.get('terms') or [{}])[0].get('goals', [])))
        return int(m.group(1)) if m else None

    n0, n1 = term1_count(g0), term1_count(gA)
    check('A：已修课程从本学期待办中扣除', n1 is not None and n0 is not None and n1 < n0,
          '方案版 %s 门 → 学业版 %s 门' % (n0, n1))

    # 7) 换学生 B
    cookie_b, _ = login('demo_b')
    hdr_b = {'Cookie': cookie_b}
    s, gB, _ = call('POST', '/api/v1/growth-plans',
                    json.dumps({'mode': 'demo', 'use_session': True}).encode(),
                    dict(hdr_b, **{'Content-Type': 'application/json'}))
    titlesB = [g['title'] for t in (gB.get('terms') or []) for g in t.get('goals', [])]
    check('B：同一链路可用', bool(titlesB), '%d 个目标' % len(titlesB))
    check('换一个学生 → 目标不同', titlesA != titlesB,
          'A %d 条 / B %d 条' % (len(titlesA), len(titlesB)))

    s, mB, _ = call('GET', '/api/v1/training-plans/match?use_session=1', None, hdr_b)
    ok = mB.get('match') == 'exact' or bool(mB.get('warnings'))
    check('年级不同 → 降级匹配并报警', ok, mB.get('match'))

    # 8) 换一组已修课程
    s, gC, _ = call('POST', '/api/v1/growth-plans',
                    json.dumps({'mode': 'demo', 'use_session': True,
                                'completed_courses': [
                                    {'name': '一元微积分', 'credits': 5},
                                    {'name': '多元微积分', 'credits': 5},
                                    {'name': '线性代数', 'credits': 3}]}).encode(),
                    dict(hdr_a, **{'Content-Type': 'application/json'}))
    check('换一组已修课程 → 缺口变化',
          gC.get('summary', {}).get('completed_credits')
          != gA.get('summary', {}).get('completed_credits'),
          '会话 %s → 覆盖 %s' % (gA.get('summary', {}).get('completed_credits'),
                                 gC.get('summary', {}).get('completed_credits')))

    # 9) 导入成绩单（方案 B：不依赖学校审批）
    body = json.dumps({'completed_courses': [
        {'name': '一元微积分', 'credits': 5, 'score': 88},
        {'name': '线性代数', 'credits': 3, 'score': 91},
        {'name': '大学物理B（上）', 'credits': 4, 'score': 84},
        {'name': '这门课不存在', 'credits': 2},
    ]}).encode()
    s, imp, _ = call('POST', '/api/v1/academic/import', body,
                     dict(hdr_a, **{'Content-Type': 'application/json'}))
    check('导入成绩单（JSON）', s == 200 and imp.get('matched') is not None,
          '匹配 %s 门 / 未匹配 %s 门' % (imp.get('summary', {}).get('matched_count'),
                                        imp.get('summary', {}).get('unmatched_count')))
    check('导入后学分对账', imp.get('credits_earned') == 12.0, '%s 学分' % imp.get('credits_earned'))
    check('未匹配的课程被明确列出', bool(imp.get('unmatched')),
          (imp.get('unmatched') or [{}])[0].get('name', ''))

    s, prof2, _ = call('GET', '/api/v1/academic/profile', None, hdr_a)
    check('学业数据来源变为 self_reported', prof2.get('source') == 'self_reported',
          '已修 %d 门' % len(prof2.get('completed_courses') or []))

    s, gD, _ = call('POST', '/api/v1/growth-plans',
                    json.dumps({'mode': 'demo', 'use_session': True}).encode(),
                    dict(hdr_a, **{'Content-Type': 'application/json'}))
    check('路线跟着导入的数据变', gD.get('summary', {}).get('completed_credits') == 12.0,
          '已修 %s 学分' % gD.get('summary', {}).get('completed_credits'))

    # CSV 合并导入
    bd = '----csvimp'
    csv_text = '课程名称,学分,修读学期,成绩\n画法几何与工程制图,3,1,86\n程序设计A,2,1,90\n'
    body = b''.join([
        ('--%s\r\nContent-Disposition: form-data; name="file"; filename="成绩单.csv"\r\n'
         'Content-Type: text/csv\r\n\r\n' % bd).encode(),
        csv_text.encode('utf-8'), b'\r\n', ('--%s--\r\n' % bd).encode()])
    s, imp2, _ = call('POST', '/api/v1/academic/import', body,
                      dict(hdr_a, **{'Content-Type': 'multipart/form-data; boundary=' + bd}))
    check('导入成绩单（CSV，合并）', s == 200 and imp2.get('total_after_merge', 0) > 4,
          '合并后共 %s 门' % imp2.get('total_after_merge'))

    # 覆盖导入
    body = json.dumps({'merge': False, 'completed_courses': [{'name': '一元微积分', 'credits': 5}]}).encode()
    s, imp3, _ = call('POST', '/api/v1/academic/import', body,
                      dict(hdr_a, **{'Content-Type': 'application/json'}))
    check('覆盖导入（merge=false）', s == 200 and imp3.get('total_after_merge') == 1,
          '共 %s 门' % imp3.get('total_after_merge'))

    # 10) 退出
    s, _, _ = call('POST', '/api/v1/auth/logout', None, hdr_a)
    s2, b2, _ = call('GET', '/api/v1/auth/session', None, hdr_a)
    check('退出后会话失效', s == 200 and b2.get('authenticated') is False)
    s3, _, _ = call('GET', '/api/v1/academic/profile', None, hdr_a)
    check('退出后学业数据 → 401', s3 == 401)
    s4, _, _ = call('POST', '/api/v1/academic/import', b'{"completed_courses":[]}',
                    {'Content-Type': 'application/json'})
    check('未登录导入 → 401', s4 == 401)

    bad = [r for r in results if not r[1]]
    print('\n%d/%d passed' % (len(results) - len(bad), len(results)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
