#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""格式矩阵自检：一次跑完五种输入，打印每种的判定与报警。用于 QA-01 / M5 验收。"""
import os
import sys

import ingest
import to_api_v1

CASES = [
    ('Word .doc（真实培养方案）',
     r'C:\Users\JUSTI\Documents\xwechat_files\wxid_lq0el398u5th22_1d3f\msg\file\2026-11\8-工学院理科试验班（智能装备）本科人才培养方案.doc', None),
    ('Word .docx（测试样本）', r'out\fixtures\示例培养方案.docx', None),
    ('含文字层 PDF（非培养方案，负例）',
     r'C:\Users\JUSTI\Documents\xwechat_files\wxid_lq0el398u5th22_1d3f\msg\file\2026-11\秋冬像素成长手帐_完整产品方案_V2.0(1).pdf', None),
    ('无文字层 PDF（无识别结果）', r'C:\Users\JUSTI\Desktop\另一学院培养方案\A专业必修.pdf', None),
    ('无文字层 PDF（带回识别结果）', r'C:\Users\JUSTI\Desktop\另一学院培养方案\A专业必修.pdf',
     r'out\other\csv\A专业必修.csv'),
    ('图片输入', r'out\render\A专业必修.png', None),
]


def main():
    print('| 场景 | 格式 | 文字层 | 课程 | 学分核平 | 完整度 | HTTP | 报警 |')
    print('|---|---|---|---|---|---|---|---|')
    for label, path, cache in CASES:
        if not os.path.exists(path):
            print('| %s | 缺失 | | | | | | |' % label)
            continue
        api, cur, comp, fmt = ingest.ingest(path, cache)
        ok = next((c['ok'] for c in comp['checks'] if c['key'] == 'credit_reconciled'), False)
        print('| %s | %s | %s | %d | %s | %s %d%% | %d | %s |' % (
            label, fmt['format'], '有' if fmt['text_layer'] else '无',
            len(api['courses']), '✓' if ok else '✗',
            comp['level'], comp['score'], to_api_v1.http_status(api),
            '、'.join(a['code'] for a in comp['alerts']) or '—'))


if __name__ == '__main__':
    sys.exit(main())
