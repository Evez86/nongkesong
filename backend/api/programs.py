#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
培养方案版本匹配：按「专业 + 入学年级」找对应的那一版。

同一专业不同年级的培养方案会变（学分、课程、模块都在改），所以不能只按专业匹配。
匹配优先级：
  1. exact                  专业相同 + 入学年级相同
  2. same_major_nearest_year 专业相同 + 取最接近的年级（并报警）
  3. none                    没有可用的方案
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLAN_DIR = os.path.join(ROOT, 'var', 'plans')


def _norm(s):
    return (s or '').replace('（', '(').replace('）', ')').replace(' ', '').strip().lower()


def _iter_plans():
    if not os.path.isdir(PLAN_DIR):
        return
    for name in sorted(os.listdir(PLAN_DIR)):
        if not name.endswith('.json'):
            continue
        path = os.path.join(PLAN_DIR, name)
        try:
            with open(path, encoding='utf-8') as f:
                api = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        yield {
            'plan_id': api.get('plan_id') or name[:-5],
            'major': api.get('program_name'),
            'cohort': api.get('cohort'),
            'course_count': len(api.get('courses') or []),
            'parse_status': api.get('parse_status'),
            'source_file': (api.get('source') or {}).get('file_name'),
        }


def index():
    return list(_iter_plans())


def match(major, enroll_year):
    """major: 专业名；enroll_year: 入学年份（int 或 None）"""
    items = index()
    target = _norm(major)
    year = None
    try:
        year = int(enroll_year) if enroll_year not in (None, '') else None
    except (TypeError, ValueError):
        year = None

    same_major = [p for p in items if target and _norm(p['major']) == target]

    if same_major and year is not None:
        exact = [p for p in same_major if p.get('cohort') is not None and int(p['cohort']) == year]
        if exact:
            p = exact[0]
            return {
                'plan_id': p['plan_id'], 'match': 'exact',
                'plan': p, 'warnings': [],
            }

    if same_major:
        with_year = [p for p in same_major if p.get('cohort') is not None]
        if with_year and year is not None:
            with_year.sort(key=lambda p: abs(int(p['cohort']) - year))
            p = with_year[0]
            return {
                'plan_id': p['plan_id'], 'match': 'same_major_nearest_year',
                'plan': p,
                'warnings': [{
                    'code': 'PLAN_YEAR_MISMATCH',
                    'message': '没有 %s 级（%s）的版本，已用 %s 级版本代替'
                               % (year, major, p['cohort']),
                }],
            }
        p = same_major[0]
        return {
            'plan_id': p['plan_id'], 'match': 'same_major_any_year',
            'plan': p,
            'warnings': [{'code': 'PLAN_YEAR_UNKNOWN',
                          'message': '该专业没有登记入学年级，无法确认版本是否对应你这一届'}],
        }

    return {
        'plan_id': None, 'match': 'none', 'plan': None,
        'warnings': [{
            'code': 'PLAN_NOT_FOUND',
            'message': '还没有收录「%s」的培养方案，请先上传，或稍后再试。' % (major or '该专业'),
        }],
        'available_majors': sorted({p['major'] for p in items if p['major']}),
    }
