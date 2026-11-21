#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BE-03 成长路线生成（§8.4）。

两层：
  1. rule   —— 确定性生成，基于培养方案的真实学分缺口，不调模型（mode=demo）
  2. ai     —— 预留 seam，未配置时返回 503，不让前端拿到假数据（mode=ai）

生成的路线必须过 validate()：
  学期 1-8 齐全且有序、goal id 唯一、course_ids 都能在方案里找到、文本长度受限。
校验不过的不返回，宁可报错也不给前端一份坏数据。
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


def build(plan, interests=None, completed_ids=None, mode='demo'):
    """plan: /api/v1/training-plans 的响应体；返回 §8.4 结构。"""
    interests = [s for s in (interests or []) if str(s).strip()][:3]
    completed = set(completed_ids or [])
    courses = plan.get('courses') or []
    groups = plan.get('groups') or []

    # 按学期归堆
    by_term = {t: [] for t in range(1, 9)}
    for c in courses:
        t = c.get('term')
        if isinstance(t, int) and 1 <= t <= 8:
            by_term[t].append(c)

    # 每个课程组的缺口：要求 - 方案内已排课程学分
    gaps = []
    for g in groups:
        need = _req(g)
        if not need:
            continue
        laid = sum(x.get('credits') or 0 for x in courses if x.get('group') == g.get('name'))
        if laid + 0.01 < need:
            last_term = max([c.get('term') or 0 for c in courses
                             if c.get('group') == g.get('name') and c.get('term')] or [0])
            gaps.append({
                'group': g.get('name'),
                'need': need,
                'laid': laid,
                'gap': round(need - laid, 2),
                'term_hint': min(8, max(1, (last_term or 2) + 1)),
            })
    gaps.sort(key=lambda x: (-x['gap'], x['group']))

    # 缺口目标别刷屏：只把最大的几条做成目标，学期上摊开，其余留在 summary
    top_gaps = [g for g in gaps if g['gap'] >= 1][:6]
    spread = [3, 4, 5, 6, 7, 7]
    for i, gp in enumerate(top_gaps):
        gp['term_hint'] = spread[i] if i < len(spread) else 8
    for gp in gaps:
        if gp not in top_gaps:
            gp['term_hint'] = None       # 不渲染成目标，只在 summary 里列出
    listed = {g['group'] for g in top_gaps}

    terms = []
    used_ids = set()
    for t in range(1, 9):
        cs = by_term[t]
        goals = []
        cs_credits = round(sum(c.get('credits') or 0 for c in cs), 2)

        if cs:
            names = '、'.join(c['name'] for c in cs[:3]) + ('等' if len(cs) > 3 else '')
            goals.append({
                'id': 'goal_t%d_1' % t,
                'title': '完成本学期 %d 门课程（%s 学分）' % (len(cs), _fmt(cs_credits)),
                'actions': ['按周拆分复习安排', '期中后核对进度 %s' % names],
                'course_ids': [c['id'] for c in cs if c.get('id')][:8],
            })

        # 缺口驱动的目标：只放在建议学期，避免八个学期都说同一件事
        for gp in gaps:
            if gp['term_hint'] == t:
                goals.append({
                    'id': 'goal_t%d_gap_%s' % (t, str(len(goals))),
                    'title': '%s 还差 %s 学分' % (gp['group'][:16], _fmt(gp['gap'])),
                    'actions': ['从该组候选课程中挑选',
                                '选课前确认先修与开课学期'],
                    'course_ids': [],
                })

        # 兴趣驱动的实践目标：放在 2/4/6 学期，节奏上更合理
        if interests and t in (2, 4, 6) and (t // 2) <= len(interests) + 1:
            idx = (t // 2) - 1
            if idx < len(interests):
                goals.append({
                    'id': 'goal_t%d_interest' % t,
                    'title': '围绕「%s」积累一次可展示的产出' % interests[idx][:20],
                    'actions': ['记录成果与用时', '整理成一段经历描述'],
                    'course_ids': [],
                })

        for g in goals:
            used_ids.add(g['id'])
        terms.append({'term': t, 'label': LABELS[t - 1], 'goals': goals})

    # 已修课程提示：只做标注，不改路线结构
    done_credits = round(sum(c.get('credits') or 0 for c in courses
                             if c.get('id') in completed), 2)

    out = {
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
            'groups_with_gap': [{'group': g['group'], 'gap': g['gap']} for g in gaps],
            'gap_goals_listed': [g['group'] for g in top_gaps],
        },
    }
    return out


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
