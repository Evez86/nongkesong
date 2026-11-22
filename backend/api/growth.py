#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BE-03 成长路线生成（§8.4）。

两层：
  1. rule   —— 确定性生成，基于培养方案的真实学分缺口，不调模型（mode=demo）
  2. ai     —— 预留 seam，未配置时返回 503，不让前端拿到假数据（mode=ai）

学业数据接入后（§8.6），路线必须**跟着已修课程变**：
  - 已修完的学期，目标从「完成 X 门课程」变成「复盘 + 巩固」
  - 缺口从「方案没排满」变成「已修多少 / 还差多少」
换一个学生 → completed 不同 → 目标不同，这是规则版验收的核心。
"""
import time
import uuid

LABELS = ['大一上', '大一下', '大二上', '大二下', '大三上', '大三下', '大四上', '大四下']
MAX_TITLE = 60
MAX_ACTIONS = 5


def _req(g):
    """组要求学分；分方向字典取最大（保守估计，避免少算）"""
    r = g.get('credits_required')
    if isinstance(r, dict):
        return max(r.values()) if r else None
    return r


def _fmt(n):
    return ('%.2f' % n).rstrip('0').rstrip('.')


def _norm(s):
    return (s or '').replace('（', '(').replace('）', ')').replace(' ', '').lower()


def _completed_index(plan, completed_ids, completed_courses):
    """把已修记录映射到方案里的课程 id。
    支持两种输入：
      completed_ids      —— ['C001', ...]（前端直接给 id）
      completed_courses  —— [{'name': '一元微积分', 'credits': 5}, ...]（学业数据）
    """
    by_id = {c.get('id'): c for c in plan.get('courses') or []}
    done_ids, unmatched = set(), []
    for cid in completed_ids or []:
        if cid in by_id:
            done_ids.add(cid)
        else:
            unmatched.append(str(cid))

    by_name = {}
    for c in plan.get('courses') or []:
        by_name.setdefault(_norm(c.get('name')), c)

    for item in completed_courses or []:
        if isinstance(item, str):
            name = item
        else:
            cid = item.get('id') or item.get('course_id')
            if cid and cid in by_id:
                done_ids.add(cid)
                continue
            name = item.get('name') or item.get('course')
        key = _norm(name)
        hit = by_name.get(key)
        if hit is None:
            # 容错：培养方案改名（如「」括号差异、加了专业前缀）
            import difflib
            best, ratio = None, 0.0
            for k, c in by_name.items():
                r = difflib.SequenceMatcher(None, k, key).ratio()
                if r > ratio:
                    best, ratio = c, r
            if ratio >= 0.85:
                hit = best
        if hit is not None:
            done_ids.add(hit.get('id'))
        else:
            unmatched.append(name)
    return done_ids, unmatched


def build(plan, interests=None, completed_ids=None, mode='demo', completed_courses=None):
    """plan: /api/v1/training-plans 的响应体；返回 §8.4 结构。"""
    interests = [s for s in (interests or []) if str(s).strip()][:3]
    courses = plan.get('courses') or []
    groups = plan.get('groups') or []

    done_ids, unmatched = _completed_index(plan, completed_ids, completed_courses)
    has_academic = bool(completed_ids or completed_courses)
    done = [c for c in courses if c.get('id') in done_ids]
    done_credits = round(sum(c.get('credits') or 0 for c in done), 2)

    # 按学期归堆
    by_term = {t: [] for t in range(1, 9)}
    for c in courses:
        t = c.get('term')
        if isinstance(t, int) and 1 <= t <= 8:
            by_term[t].append(c)

    # 每个课程组：要求 / 方案内已排 / 已修 / 缺口
    gaps = []
    for g in groups:
        need = _req(g)
        if not need:
            continue
        laid = sum(x.get('credits') or 0 for x in courses if x.get('group') == g.get('name'))
        earned = sum(x.get('credits') or 0 for x in done if x.get('group') == g.get('name'))
        if has_academic:
            remain = round(need - earned, 2)
        else:
            remain = round(need - laid, 2)
        if remain > 0.01:
            gaps.append({'group': g['name'], 'need': need, 'laid': round(laid, 2),
                         'earned': round(earned, 2), 'gap': remain})

    gaps.sort(key=lambda x: (-x['gap'], x['group']))
    top_gaps = gaps[:6]
    spread = [3, 4, 5, 6, 7, 7]
    for i, gp in enumerate(top_gaps):
        gp['term_hint'] = spread[i] if i < len(spread) else 8
    for gp in gaps:
        if gp not in top_gaps:
            gp['term_hint'] = None

    terms = []
    for t in range(1, 9):
        cs = by_term[t]
        goals = []
        cs_credits = round(sum(c.get('credits') or 0 for c in cs), 2)
        all_done = bool(cs) and all(c.get('id') in done_ids for c in cs)

        if cs and all_done:
            goals.append({
                'id': 'goal_t%d_1' % t,
                'title': '本学期 %d 门课程已修完（%s 学分）' % (len(cs), _fmt(cs_credits)),
                'actions': ['复盘成绩，整理课程笔记', '把课程成果归到作品集'],
                'course_ids': [c['id'] for c in cs if c.get('id')][:8],
            })
        elif cs:
            left = [c for c in cs if c.get('id') not in done_ids]
            goals.append({
                'id': 'goal_t%d_1' % t,
                'title': '完成本学期 %d 门课程（%s 学分）' % (len(left), _fmt(cs_credits)),
                'actions': ['按周拆分复习安排',
                            '期中后核对进度 %s' % '、'.join(c['name'] for c in left[:2])],
                'course_ids': [c['id'] for c in left if c.get('id')][:8],
            })

        for gp in top_gaps:
            if gp['term_hint'] == t:
                if has_academic and gp['earned'] > 0:
                    title = '%s 已修 %s，还差 %s' % (gp['group'][:14], _fmt(gp['earned']), _fmt(gp['gap']))
                    actions = ['从剩余候选课程中挑选', '选课前确认先修与开课学期']
                else:
                    title = '%s 还差 %s 学分' % (gp['group'][:16], _fmt(gp['gap']))
                    actions = ['从该组候选课程中挑选', '选课前确认先修与开课学期']
                goals.append({
                    'id': 'goal_t%d_gap_%d' % (t, len(goals)),
                    'title': title, 'actions': actions, 'course_ids': [],
                })

        if interests and t in (2, 4, 6):
            idx = (t // 2) - 1
            if idx < len(interests):
                goals.append({
                    'id': 'goal_t%d_interest' % t,
                    'title': '围绕「%s」积累一次可展示的产出' % interests[idx][:20],
                    'actions': ['记录成果与用时', '整理成一段经历描述'],
                    'course_ids': [],
                })

        terms.append({'term': t, 'label': LABELS[t - 1], 'goals': goals})

    return {
        'id': 'growth_' + uuid.uuid4().hex[:8],
        'plan_id': plan.get('plan_id'),
        'source': 'demo',
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'terms': terms,
        'summary': {
            'mode': mode,
            'interests': interests,
            'credits_in_plan': round(sum(c.get('credits') or 0 for c in courses), 2),
            'completed_credits': done_credits or None,
            'completed_count': len(done),
            'unmatched_completed': unmatched[:10],
            'groups_with_gap': [{'group': g['group'], 'gap': g['gap'],
                                 'earned': g['earned'] if has_academic else None} for g in gaps],
            'gap_goals_listed': [g['group'] for g in top_gaps],
            'based_on': 'academic' if has_academic else 'plan_only',
        },
    }


def validate(out, plan=None):
    """返回问题列表；空列表表示可以直接返回给前端。"""
    problems = []
    terms = out.get('terms') or []
    if len(terms) != 8:
        problems.append('学期数应为 8，实际 %d' % len(terms))
    nums = [x.get('term') for x in terms]
    if nums != list(range(1, 9)):
        problems.append('term 编号必须是 1..8 且有序，实际 %s' % nums)

    known = {c.get('id') for c in (plan or {}).get('courses') or []}
    seen = set()
    for x in terms:
        for g in x.get('goals') or []:
            gid = g.get('id')
            if not gid:
                problems.append('term %s 有 goal 缺 id' % x.get('term'))
            elif gid in seen:
                problems.append('goal id 重复：%s' % gid)
            seen.add(gid)
            if not (g.get('title') or '').strip():
                problems.append('%s 缺 title' % gid)
            elif len(g['title']) > MAX_TITLE:
                problems.append('%s title 超长（%d）' % (gid, len(g['title'])))
            acts = g.get('actions') or []
            if not acts:
                problems.append('%s 缺 actions' % gid)
            elif len(acts) > MAX_ACTIONS:
                problems.append('%s actions 超过 %d 条' % (gid, MAX_ACTIONS))
            for cid in g.get('course_ids') or []:
                if cid not in known:
                    problems.append('%s 引用了不存在的课程 %s' % (gid, cid))
    if out.get('source') not in ('demo', 'ai'):
        problems.append('source 只能是 demo 或 ai')
    return problems
