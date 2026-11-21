#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
毕业缺口分析（后端任务的下一层：规划生成的前提）
用法：
    python gaps.py out/curriculum.json 植物模块 done_sample.json

done_sample.json 形如 ["一元微积分", "线性代数", "12314001", ...]（课程名或编号）
"""
import json
import sys


def main(cur_path, track, done_path):
    d = json.load(open(cur_path, encoding='utf-8'))
    done = set(json.load(open(done_path, encoding='utf-8')))
    tracks = sorted({k for m in d['modules'] for g in m['groups']
                     if isinstance(g.get('credits_required'), dict)
                     for k in g['credits_required']})
    track = track or (tracks[0] if tracks else None)

    print('培养方向：%s' % (track or '单一'))
    print()
    print('| 模块 | 课程组 | 需修 | 已修 | 缺口 | 说明 |')
    print('|---|---|---|---|---|---|')
    total_need = total_got = 0.0
    for m in d['modules']:
        if m.get('role') == 'practice_breakdown':
            continue
        for g in m['groups']:
            req = g.get('credits_required')
            need = req.get(track) if isinstance(req, dict) else req
            courses = [c for s in g['subgroups'] for c in s['courses']]

            def mine(c):
                tr = c.get('track')
                return tr is None or tr == track or (tracks and tr not in tracks)

            # 互斥方向组：取该方向课程的实际值，而不是全部相加
            got = sum(c['credits'] for c in courses if mine(c)
                      and (c['name'] in done or (c.get('code') and c['code'] in done)))
            if need is None:
                need = sum(c['credits'] for c in courses if mine(c))
                note = '未声明，按课程合计'
            else:
                note = ''
            gap = round(need - got, 2)
            if not courses and need:
                note = (note + '；' if note else '') + '文档未列课程明细'
            print('| %s | %s | %s | %s | %s | %s |' % (
                m['name'], g['name'], _f(need), _f(got), _f(gap), note))
            total_need += need or 0
            total_got += got
    print('| **合计** | | **%s** | **%s** | **%s** | |' % (
        _f(total_need), _f(total_got), _f(round(total_need - total_got, 2))))


def _f(v):
    if v is None:
        return '—'
    return ('%.2f' % v).rstrip('0').rstrip('.')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
         sys.argv[3] if len(sys.argv) > 3 else 'done_sample.json')
