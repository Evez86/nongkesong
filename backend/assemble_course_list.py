#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第二个数据形态的适配器：教务系统"课程体系明细"导出（按课程性质分组的课程清单）。

与第一份（Word 版培养方案）的区别：
  - 没有"XX：N 学分"的章节标题，课程组由【课程性质】列承载；
  - 不声明模块/组学分，只能由课程累加；
  - 多了【完成情况】【已获学分】两列 —— 那是学籍执行数据，不属于培养方案；
  - 学期是纯数字（1~11），不是"1秋/2春"。

输出仍然写进同一套 schema（modules → groups → subgroups → courses），
证明"变的是适配器，不是数据模型"。
"""
import csv
import json
import sys


def load(path):
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if not r.get('name'):
                continue
            rows.append(r)
    return rows


def build(rows, meta):
    issues = []
    groups = {}
    order = []
    for r in rows:
        g = r['group'].strip()
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append(r)

    modules = []
    gid = 0
    mod = {'id': 'M1', 'name': '课程体系', 'credits_required': None,
           'groups': [], 'computed_credits': None}
    courses = []
    seq = 0
    for gname in order:
        gid += 1
        items = groups[gname]
        subs = []
        gsum = 0.0
        for r in items:
            seq += 1
            cr = float(r['credits'])
            gsum += cr
            terms = []
            try:
                terms = ['第%d学期' % int(float(r['term']))] if r.get('term') else []
            except Exception:
                terms = []
            c = {
                'id': 'O%03d' % seq,
                'code': r['code'] or None,
                'name': r['name'].strip(),
                'unit': None,
                'type': 'required' if r['attr'].strip() == '必修' else 'elective',
                'type_raw': r['attr'].strip(),
                'nature_raw': r['nature'].strip(),
                'hours': {'raw': r['hours'].strip()} if r.get('hours') else None,
                'credits': cr,
                'terms': terms,
                'term_raw': r.get('term', '').strip(),
                'module': '课程体系',
                'group': gname,
            }
            courses.append(c)
        subs.append({'name': '默认组', 'credits_required': None, 'courses': []})
        mod['groups'].append({
            'id': 'M1.G%d' % gid,
            'name': gname,
            'credits_required': None,          # 该导出不声明组学分
            'computed_credits': round(gsum, 2),
            'subgroups': subs,
        })
    # 把课程塞进对应组的默认子组
    by_group = {g['name']: g for g in mod['groups']}
    for c in courses:
        by_group[c['group']]['subgroups'][0]['courses'].append(
            {k: v for k, v in c.items() if k not in ('module', 'group')})
    mod['computed_credits'] = round(sum(c['credits'] for c in courses), 2)
    modules.append(mod)

    # ---- 校验 / 体检 ----
    total = mod['computed_credits']
    issues.append({'level': 'info', 'code': 'TOTAL_SUM',
                   'message': '课程累加 %.2f 学分（该导出未声明毕业总学分，无法核平）' % total})

    for g in mod['groups']:
        issues.append({'level': 'info', 'code': 'GROUP_SUM',
                       'message': '%s：%d 门，合计 %.2f 学分（文档未声明组学分）'
                                  % (g['name'], len(g['subgroups'][0]['courses']),
                                     g['computed_credits'])})

    # 1) 学期取值异常
    bad_terms = {}
    for c in courses:
        t = c['term_raw']
        if t.isdigit() and int(t) > 8:
            bad_terms.setdefault(t, []).append(c['name'])
    for t, names in sorted(bad_terms.items()):
        issues.append({'level': 'warning', 'code': 'TERM_OUT_OF_RANGE',
                       'message': '开设学期=%s 超出四年制 1-8 学期范围（%s）——该字段可能是教务系统学期码，需确认语义'
                                  % (t, '、'.join(names))})

    # 2) 学时 < 学分：总学时列疑似混入了"周"
    odd = [c for c in courses if c.get('hours') and c['hours']['raw'].replace('.', '').isdigit()
           and float(c['hours']['raw']) < 8]
    if odd:
        issues.append({'level': 'warning', 'code': 'HOURS_SUSPECT',
                       'message': '%d 门课的总学时小于 8（如 %s），推测该列对实习/论文写的是"周"，口径不统一'
                                  % (len(odd), '、'.join('%s=%s' % (c['name'], c['hours']['raw'])
                                                         for c in odd[:3]))})

    # 3) 同类字段重复
    issues.append({'level': 'warning', 'code': 'REDUNDANT_COLUMN',
                   'message': '【课程性质】与【课程属性】语义重叠（专业必修/必修），后者在本导出中恒为必修/选修，'
                              '建议只保留一个作为 type，另一个降级为 group'})
    variants = sorted({c['nature_raw'] for c in courses})
    if len(variants) != len({c['group'] for c in courses}):
        issues.append({'level': 'info', 'code': 'NATURE_VARIANT',
                       'message': '课程性质存在变体写法：%s（“专业选修课”应按“专业选修”归一）'
                                  % '、'.join(variants)})

    # 4) 学生执行数据与培养方案混在一张表
    done = [r for r in rows if r['status'].strip()]
    if done:
        issues.append({'level': 'info', 'code': 'MIXED_STUDENT_DATA',
                       'message': '本导出含 %d 条【完成情况/已获学分】，属于学籍执行数据，已从培养方案中剥离到 student_records'
                                  % len(done)})

    student_records = [{
        'code': r['code'], 'name': r['name'].strip(),
        'status': r['status'].strip(),
        'earned_credits': float(r['earned']) if r['earned'].strip() else None,
        'term': r['term'].strip(),
    } for r in done]

    return {
        'schema_version': '0.2',
        'meta': meta,
        'modules': modules,
        'courses': courses,
        'student_records': student_records,
        'issues': issues,
    }


if __name__ == '__main__':
    rows = load(sys.argv[1])
    meta = {
        'source': 'course_list_export',
        'school': None,
        'major': None,
        'duration_years': None,
        'total_credits': None,
        'note': '教务系统“课程体系明细”导出，8 个分文件按课程性质拆分；无模块学分声明',
    }
    data = build(rows, meta)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps({'courses': len(data['courses']),
                      'groups': len(data['modules'][0]['groups']),
                      'records': len(data['student_records']),
                      'issues': len(data['issues'])}, ensure_ascii=False))
