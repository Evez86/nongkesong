#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学业数据（学号 → 专业 / 入学年级 / 当前学期 / 课表 / 已修课程）。

契约要点：**每个字段都带状态**。取不到的不是缺省为空，而是明确标
`{"status": "unavailable", "reason": "..."}`，前端据此显示「暂未同步」。
这样用户永远知道哪些是真数据、哪些是没拿到，而不是以为数据错了。

三种数据源：
  mock   —— 本地开发，两个演示学生（验收「换学生结果会变」）
  file   —— 学校导出的 JSON（PINE_ACADEMIC_SOURCE 指向文件），用于联调
  live   —— 真实教务接口（未接；配置后由 SchoolProvider 实现）
"""
import json
import os

MODE = os.environ.get('PINE_ACADEMIC_MODE', 'mock')
SOURCE_FILE = os.environ.get('PINE_ACADEMIC_SOURCE', '')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMPORT_DIR = os.path.join(ROOT, 'var', 'academic')

# 契约里约定的字段清单（顺序即前端展示顺序）
FIELDS = ['major', 'enroll_year', 'current_term', 'timetable', 'completed_courses',
          'gpa', 'class_name', 'advisor']

# 两个演示学生：已修课程不同，用来验证「换一组已修课程，路线目标会变」
MOCK_ACADEMIC = {
    'demo_a': {
        'major': '工科试验班（智能装备）',
        'enroll_year': 2024,
        'current_term': 3,
        'timetable': [
            {'course': '概率论与数理统计', 'weekday': 1, 'period': '1-2', 'place': '三教 204'},
            {'course': '大学物理B（下）', 'weekday': 2, 'period': '3-4', 'place': '三教 108'},
            {'course': '工程力学A（上）', 'weekday': 3, 'period': '1-2', 'place': '工院 401'},
            {'course': '机械设计基础', 'weekday': 4, 'period': '5-6', 'place': '工院 302'},
        ],
        'completed_courses': [
            {'name': '一元微积分', 'credits': 5.0, 'term': 1, 'score': 88},
            {'name': '线性代数', 'credits': 3.0, 'term': 2, 'score': 91},
            {'name': '大学物理B（上）', 'credits': 4.0, 'term': 2, 'score': 84},
            {'name': '画法几何与工程制图', 'credits': 3.0, 'term': 1, 'score': 86},
            {'name': '程序设计A', 'credits': 2.0, 'term': 1, 'score': 90},
            {'name': 'Academic Writing（1）', 'credits': 2.0, 'term': 1, 'score': 85},
        ],
    },
    'demo_b': {
        'major': '工科试验班（智能装备）',
        'enroll_year': 2023,
        'current_term': 5,
        'timetable': [
            {'course': '控制工程基础', 'weekday': 1, 'period': '3-4', 'place': '工院 205'},
            {'course': '液压与气压传动', 'weekday': 3, 'period': '5-6', 'place': '工院 107'},
        ],
        'completed_courses': [
            {'name': '一元微积分', 'credits': 5.0, 'term': 1, 'score': 76},
            {'name': '多元微积分', 'credits': 5.0, 'term': 2, 'score': 79},
            {'name': '线性代数', 'credits': 3.0, 'term': 2, 'score': 82},
            {'name': '大学物理B（上）', 'credits': 4.0, 'term': 3, 'score': 80},
            {'name': '大学物理B（下）', 'credits': 3.5, 'term': 4, 'score': 78},
            {'name': '基础化学', 'credits': 2.0, 'term': 1, 'score': 83},
            {'name': '工程力学A（上）', 'credits': 3.0, 'term': 3, 'score': 81},
            {'name': '材料与制造技术及实践', 'credits': 6.0, 'term': 4, 'score': 88},
        ],
    },
}


def mode():
    return MODE


def _status(ok, reason=None):
    return {'status': 'available'} if ok else {'status': 'unavailable', 'reason': reason}


def _from_file(student_id):
    if not SOURCE_FILE or not os.path.exists(SOURCE_FILE):
        return None
    try:
        data = json.load(open(SOURCE_FILE, encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data.get(student_id)
    return None


# ============================================================ 学生自己导入
# 方案 B：学生在教务系统「导出成绩单/课表」→ 上传 → 解析成已修课程。
# 数据来源标记 self_reported，前端显示「你导入的」，不冒充学校同步。

NAME_ALIASES = ['课程名称', '课程名', '课程', '名称', 'course', 'course_name', 'name']
CREDIT_ALIASES = ['学分', '课程学分', 'credits', 'credit']
TERM_ALIASES = ['学期', '修读学期', '开课学期', 'term', 'semester']
SCORE_ALIASES = ['成绩', '分数', '得分', 'score', 'grade']


def _import_path(student_id):
    safe = ''.join(ch for ch in str(student_id) if ch.isalnum() or ch in '-_')
    return os.path.join(IMPORT_DIR, '%s.json' % (safe or 'local'))


def load_imported(student_id):
    try:
        with open(_import_path(student_id), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_imported(student_id, courses, merge=True):
    os.makedirs(IMPORT_DIR, exist_ok=True)
    existing = load_imported(student_id) if merge else None
    prev = (existing or {}).get('completed_courses') or []
    by_name = {(_norm(c.get('name'))): c for c in prev if c.get('name')}
    for c in courses:
        key = _norm(c.get('name'))
        if not key:
            continue
        if key in by_name:
            by_name[key].update({k: v for k, v in c.items() if v is not None})
        else:
            by_name[key] = dict(c)
    merged = sorted(by_name.values(), key=lambda c: (c.get('term') or 99, c.get('name') or ''))
    payload = {
        'student_id': student_id,
        'completed_courses': merged,
        'source': 'self_reported',
        'updated_at': __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime()),
    }
    with open(_import_path(student_id), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _norm(s):
    return (s or '').replace('（', '(').replace('）', ')').replace(' ', '').strip().lower()


def _to_float(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _pick(header, aliases):
    for i, h in enumerate(header):
        if _norm(h) in [_norm(a) for a in aliases]:
            return i
    return None


def parse_csv(text):
    """带表头或不带表头都吃。返回 [(course_dict)]"""
    import csv
    import io
    text = text.lstrip('\ufeff')
    sample = text.splitlines()[0] if text.splitlines() else ''
    delim = max([',', '\t', ';'], key=lambda d: sample.count(d))
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not rows:
        return []
    header = rows[0]
    ni = _pick(header, NAME_ALIASES)
    if ni is None:                       # 没表头：按位置猜
        cols = {'name': 0, 'credits': 1, 'score': 2}
        body = rows
    else:
        ci = _pick(header, CREDIT_ALIASES)
        ti = _pick(header, TERM_ALIASES)
        si = _pick(header, SCORE_ALIASES)
        cols = {'name': ni, 'credits': ci, 'term': ti, 'score': si}
        body = rows[1:]

    out = []
    for r in body:
        def get(k):
            i = cols.get(k)
            return r[i].strip() if i is not None and i < len(r) else None
        name = get('name')
        if not name or name in ('合计', '总学分'):
            continue
        out.append({
            'name': name,
            'credits': _to_float(get('credits')),
            'term': _to_float(get('term')),
            'score': _to_float(get('score')),
        })
    return out


def parse_txt(text):
    """一行一门课：『高等数学 5 88』『高等数学,5,88』或只有课程名。"""
    import re
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p for p in re.split(r'[\s,，\t]+', line) if p]
        name = parts[0]
        nums = [p for p in parts[1:] if re.fullmatch(r'\d+(\.\d+)?', p)]
        out.append({
            'name': name,
            'credits': float(nums[0]) if nums else None,
            'score': float(nums[1]) if len(nums) > 1 else None,
            'term': None,
        })
    return out


def parse_payload(payload, filename=''):
    """payload: dict(JSON) / str(CSV/TXT) / bytes。返回 (courses, 格式说明)"""
    name = (filename or '').lower()
    if isinstance(payload, dict):
        courses = payload.get('completed_courses') or payload.get('courses') or []
        if payload.get('text'):
            return parse_txt(payload['text']), 'text'
        norm = [{'name': c.get('name') or c.get('course'), 'credits': c.get('credits'),
                 'term': c.get('term'), 'score': c.get('score')} for c in courses]
        return [c for c in norm if c.get('name')], 'json'
    if isinstance(payload, bytes):
        payload = payload.decode('utf-8-sig', 'replace')
    text = payload or ''
    if name.endswith('.json') or text.lstrip().startswith(('{', '[')):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return parse_payload(data), 'json'
            return parse_payload({'completed_courses': data}), 'json'
        except json.JSONDecodeError:
            pass
    if name.endswith('.csv') or ',' in (text.splitlines()[0] if text.splitlines() else ''):
        return parse_csv(text), 'csv'
    return parse_txt(text), 'text'


# ============================================================ 与方案匹配
def match_courses(plan_courses, imported):
    """把导入的课程名对到培养方案里的课程。返回 (matched, unmatched)"""
    import difflib
    by_name = {}
    for c in plan_courses or []:
        by_name.setdefault(_norm(c.get('name')), c)
    matched, unmatched = [], []
    for item in imported:
        key = _norm(item.get('name'))
        hit = by_name.get(key)
        ratio = 1.0 if hit else 0.0
        if hit is None:
            best, ratio = None, 0.0
            for k, c in by_name.items():
                r = difflib.SequenceMatcher(None, k, key).ratio()
                if r > ratio:
                    best, ratio = c, r
            if ratio >= 0.85:
                hit = best
        if hit is None:
            unmatched.append({'name': item.get('name'), 'reason': '培养方案里找不到同名课程'})
        else:
            matched.append({
                'name': item.get('name'),
                'course_id': hit.get('id'),
                'plan_name': hit.get('name'),
                'credits': item.get('credits') if item.get('credits') is not None else hit.get('credits'),
                'score': item.get('score'),
                'fuzzy': ratio < 1.0,
            })
    return matched, unmatched


def fetch(student):
    """student: {'student_id','name','major','enroll_year'}（来自会话）
    返回 (payload, missing)

    数据来源优先级：学生自己导入（self_reported） > 学校导出/接口 > 演示数据。
    导入的数据永远排在前面——学生自己确认过的，比我们猜的准。
    """
    sid = (student or {}).get('student_id')
    if not sid:
        raise ValueError('缺少学号')

    raw, source = None, 'none'
    if MODE == 'mock':
        key = student.get('_mock_key') or 'demo_a'
        raw, source = MOCK_ACADEMIC.get(key), 'mock'
    else:
        raw = _from_file(sid)
        source = 'file' if raw else 'none'

    raw = raw or {}
    profile = {
        'major': raw.get('major') or student.get('major'),
        'enroll_year': raw.get('enroll_year') or student.get('enroll_year'),
        'current_term': raw.get('current_term'),
    }
    timetable = raw.get('timetable')
    completed = raw.get('completed_courses')

    imported = load_imported(sid)
    if imported and imported.get('completed_courses'):
        completed = imported['completed_courses']
        source = 'self_reported'

    field_status = {
        'major': _status(bool(profile['major']), '登录返回中不含专业，需教务数据'),
        'enroll_year': _status(bool(profile['enroll_year']), '登录返回中不含入学年份'),
        'current_term': _status(profile['current_term'] is not None, '未导入，可在“当前学期”里手动选'),
        'timetable': _status(bool(timetable), '课表暂不支持导入，可稍后补'),
        'completed_courses': _status(bool(completed), '还没有导入成绩单，可在课程簿里导入'),
        'gpa': _status(False, '本轮不采集绩点，避免不必要地保存敏感成绩'),
        'class_name': _status(False, '班级信息未开放'),
        'advisor': _status(False, '导师信息未开放'),
    }
    missing = [k for k in FIELDS if field_status[k]['status'] == 'unavailable']

    payload = {
        'student': {'student_id': sid, 'name': (student or {}).get('name')},
        'profile': profile,
        'timetable': timetable or [],
        'completed_courses': completed or [],
        'field_status': field_status,
        'missing_fields': missing,
        'source': source,
        'updated_at': (imported or {}).get('updated_at'),
    }
    return payload, missing
