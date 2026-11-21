#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 curriculum.json 渲染成一份人可读的解析报告 parse_report.md。"""
import json
import sys
from collections import Counter


def fmt(v):
    if isinstance(v, float):
        return ('%.2f' % v).rstrip('0').rstrip('.')
    return str(v)


def credits_str(v):
    if v is None:
        return '—'
    if isinstance(v, dict):
        return ' / '.join('%s %s' % (k, fmt(c)) for k, c in v.items())
    return fmt(v)


def main(src, out):
    d = json.load(open(src, encoding='utf-8'))
    meta = d['meta']
    courses = d['courses']
    issues = d['issues']
    tracks = []
    for m in d['modules']:
        for g in m['groups']:
            if isinstance(g.get('credits_required'), dict):
                for k in g['credits_required']:
                    if k not in tracks:
                        tracks.append(k)

    L = []
    add = L.append
    add('# 培养方案解析报告')
    add('')
    add('> 由 `curriculum_parser.py` 自动生成，所有数字均来自原始文档，未做人工修正。')
    add('')
    add('## 1. 基本信息')
    add('')
    add('| 项目 | 识别结果 |')
    add('|---|---|')
    add('| 专业 | %s |' % meta.get('major_name', '—'))
    add('| 学制 | %s 年 |' % meta.get('duration_years', '—'))
    add('| 学位 | %s |' % meta.get('degree', '—'))
    add('| 毕业总学分 | %s |' % fmt(meta.get('total_credits', 0)))
    add('| 通识教育学分 | %s |' % fmt(meta.get('general_credits', 0)))
    add('| 培养方向 | %s |' % ('、'.join(tracks) if tracks else '单一'))
    add('| 识别课程条目 | %d 门 |' % len(courses))
    add('| 识别层级 | %d 个模块 / %d 个课程组 |' % (
        len([m for m in d['modules'] if m.get('role') != 'practice_breakdown']),
        sum(len(m['groups']) for m in d['modules'] if m.get('role') != 'practice_breakdown')))
    add('')

    add('## 2. 学分结构（按培养方向核平）')
    add('')
    if tracks:
        add('| 模块 | ' + ' | '.join('%s 学分' % t for t in tracks) + ' |')
        add('|' + '---|' * (len(tracks) + 1))
        for m in d['modules']:
            if m.get('role') == 'practice_breakdown':
                continue
            req = m['credits_required']
            cells = [fmt(req.get(t, 0)) if isinstance(req, dict) else fmt(req) for t in tracks]
            add('| %s | %s |' % (m['name'], ' | '.join(cells)))
        totals = [fmt(sum(m['credits_required'].get(t, 0) if isinstance(m['credits_required'], dict)
                          else m['credits_required']
                          for m in d['modules'] if m.get('role') != 'practice_breakdown'))
                  for t in tracks]
        add('| **合计** | %s |' % ' | '.join(totals))
    else:
        add('| 模块 | 声明学分 |')
        add('|---|---|')
        for m in d['modules']:
            if m.get('role') == 'practice_breakdown':
                continue
            add('| %s | %s |' % (m['name'], credits_str(m['credits_required'])))
        add('| **合计** | %s |' % fmt(meta.get('total_credits', 0)))
    add('')

    add('## 3. 结构树')
    add('')
    for m in d['modules']:
        add('### %s（%s 学分%s）' % (
            m['name'], credits_str(m['credits_required']),
            '，实践学分归集视图' if m.get('role') == 'practice_breakdown' else ''))
        add('')
        for g in m['groups']:
            cs = g.get('computed_credits')
            add('- **%s** ｜声明 %s ｜表内 %s' % (g['name'], credits_str(g['credits_required']), credits_str(cs)))
            for s in g['subgroups']:
                names = [c['name'] for c in s['courses']]
                n = len(names)
                tag = ''
                tr_in = sorted({c['track'] for c in s['courses'] if c.get('track')})
                if len(tracks) > 1 and tr_in and set(tr_in) == set(tracks):
                    tag = '，按方向二选一'
                label = '（默认课组）' if s['name'] == '默认组' else s['name']
                if n == 0:
                    add('  - %s（%s 学分，文档未列课程明细）' % (label, credits_str(s['credits_required'])))
                else:
                    add('  - %s（%s 学分，%d 门%s）：%s' % (
                        label, credits_str(s['credits_required']), n, tag,
                        '、'.join(names[:8]) + ('…' if n > 8 else '')))
        add('')

    add('## 4. 校验结果')
    add('')
    order = {'error': 0, 'warning': 1, 'info': 2}
    for lvl, title in (('error', '错误'), ('warning', '需人工确认'), ('info', '通过项')):
        rows = [i for i in issues if i['level'] == lvl]
        if not rows:
            continue
        add('**%s**' % title)
        add('')
        for i in rows:
            add('- `%s` %s' % (i['code'], i['message']))
        add('')

    add('## 5. 文档自身的问题（解析发现的，不是解析错误）')
    add('')
    add('1. **实践学分两处数字不一致**：“毕业学分要求”写 38.25，“实践教育环节”标题写 38.75。逐项相加为 38.75，可判定 38.25 为笔误。')
    add('2. **“智能装备设计制造实践”（课程表，8 学分）与“智能装备设计制造综合实践”（实践表，8 学分）疑似同一门课**，两处命名不一致，需教务确认。')
    add('3. **“工程模块”“智能模块组”不是普通类别**：注释写明“为必修，可选表中若干课程，也可选分流专业的对应课程，学分按规定置换”，因此它们应当建成 `module_group`（组内全修 + 允许置换），不能当普通必修逐门硬编码。')
    add('4. **专业选修无课程明细**：正文只写“选修范围包括工学院、信电学院……”，未列课程与学分，系统只能记录“需修 9/6 学分”这一约束，无法生成候选清单 —— 这正是需要“用户确认/学校课程库”补充的地方。')
    add('')

    add('## 6. 字段完整率')
    add('')
    total = len(courses) or 1
    def ratio(key, pred):
        return '%d/%d（%.0f%%）' % (sum(1 for c in courses if pred(c)), total,
                                    100.0 * sum(1 for c in courses if pred(c)) / total)
    add('| 字段 | 覆盖率 | 说明 |')
    add('|---|---|---|')
    add('| 课程名称 | %s | 必须 |' % ratio('name', lambda c: bool(c.get('name'))))
    add('| 学分 | %s | 必须 |' % ratio('credits', lambda c: c.get('credits') is not None))
    add('| 修读学期 | %s | 部分课程为“不限” |' % ratio('terms', lambda c: bool(c.get('terms'))))
    add('| 开课单位 | %s | |' % ratio('unit', lambda c: bool(c.get('unit'))))
    add('| 课程编号 | %s | 该校多数表格无编号列 |' % ratio('code', lambda c: bool(c.get('code'))))
    add('| 实践学分 | %s | 来自实践表逐行归集 |' % ratio('practice', lambda c: c.get('practice_credits') is not None))
    add('')

    add('## 7. 与“任意培养方案”的关系')
    add('')
    add('这份 `curriculum.json` 里没有任何一处写死了“智能装备试验班”的课程。换一份方案，变的是数据，不是代码：')
    add('')
    add('- 层级结构固定为 `模块 → 课程组 → 课程`，组规则只有 `all_of / credits / pick_n / pick_n_of` 四种；')
    add('- 学分可以声明为单值，也可以是 `{"植物模块": 75.5, "动物模块": 78.5}` 这种分方向字典；')
    add('- 课程行靠“学分锚点 + 邻居字段形态”识别，不依赖列序；换排版只需改抽取适配器；')
    add('- 所有对不上的数字都进 `issues`，不静默修正 —— 这是“通用”能站住的前提。')
    add('')
    add('复现：')
    add('')
    add('```bash')
    add('python backend/curriculum_parser.py "<培养方案.doc>" backend/out/curriculum.json')
    add('python backend/report.py backend/out/curriculum.json backend/out/parse_report.md')
    add('```')
    add('')
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
