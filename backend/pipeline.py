#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一条命令跑完整条工作流（给新人和 CI 用）。

  python pipeline.py 培养方案.docx
  python pipeline.py 扫描件.pdf --ocr-cache rows.csv
  python pipeline.py a.docx b.pdf --out out/plan.json

流程：格式探测 → 适配器抽取 → 结构化 → 归一化 → 完整度校验 → API 响应 → 报告
产物：out/api/plan.json（接口响应体）+ out/pipeline_report.md（人看的报告）
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, 'api')):
    if p not in sys.path:
        sys.path.insert(0, p)

import ingest  # noqa: E402
import to_api_v1  # noqa: E402

FMT_NOTE = {
    'docx': 'Word 原件，字段最全',
    'word97': 'Word 97 原件，建议另存为 .docx',
    'pdf_text': '含文字层 PDF，表格靠坐标还原',
    'pdf_vector': '无文字层 PDF，必须转图识别',
    'image': '图片，无版面结构',
}


def write_report(path, files, api, comp, fmt):
    L = ['# 解析报告', '']
    L.append('## 1. 输入')
    L.append('')
    L.append('| 文件 | 格式 | 说明 |')
    L.append('|---|---|---|')
    for f in files:
        L.append('| %s | %s | %s |' % (f, fmt.get('format', ''),
                                       FMT_NOTE.get(fmt.get('format', ''), '')))
    L.append('')
    L.append('## 2. 结果')
    L.append('')
    L.append('| 项 | 值 |')
    L.append('|---|---|')
    L.append('| 专业 | %s |' % (api.get('program_name') or '—'))
    L.append('| 课程 | %d 门 |' % len(api['courses']))
    L.append('| 课程组 | %d 个 |' % len(api['groups']))
    cs = api['credit_summary']
    L.append('| 必修学分 | %s |' % cs['parsed_credits'])
    L.append('| 选修池 | %s |' % cs['elective_pool_credits'])
    L.append('| 毕业要求 | %s |' % (cs['graduation_target_credits'] if cs['graduation_target_credits'] is not None else '文档未声明'))
    L.append('| 完整度 | %s（%d%%） |' % (comp['level'], comp['score']))
    L.append('| HTTP | %d |' % to_api_v1.http_status(api))
    L.append('')
    L.append('## 3. 完整性检查')
    L.append('')
    L.append('| 检查项 | 结果 | 说明 |')
    L.append('|---|---|---|')
    for c in comp['checks']:
        L.append('| `%s` | %s | %s |' % (c['key'], '✓' if c['ok'] else '✗', c['detail']))
    L.append('')
    if comp['alerts']:
        L.append('## 4. 报警')
        L.append('')
        for a in comp['alerts']:
            L.append('**%s**（%s）：%s' % (a['code'], a['severity'], a['message']))
            L.append('')
            L.append('> 建议：%s' % a['user_action'])
            L.append('')
    L.append('## 5. 课程组')
    L.append('')
    L.append('| 组 | 规则 | 要求 | 实际合计 | 门数 |')
    L.append('|---|---|---|---|---|')
    for g in api['groups']:
        req = g.get('credits_required')
        if isinstance(req, dict):
            req = ' / '.join('%s %s' % (k, v) for k, v in req.items())
        L.append('| %s | %s | %s | %s | %d |' % (
            g['name'], g['rule'], req if req is not None else '未声明',
            g.get('computed_credits'), g.get('course_count') or 0))
    L.append('')
    L.append('## 6. 建议上传格式')
    L.append('')
    ru = comp['recommended_upload']
    L.append('**%s** —— %s' % (ru['label'], ru['reason']))
    L.append('')
    L.append('| 优先级 | 格式 | 说明 |')
    L.append('|---|---|---|')
    for i, r in enumerate(ru['rank'], 1):
        L.append('| %d | %s | %s |' % (i, r['label'], r['note']))
    L.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description='培养方案解析：一条命令跑完整条工作流')
    ap.add_argument('files', nargs='+')
    ap.add_argument('--ocr-cache', help='无文字层文件的识别结果 CSV')
    ap.add_argument('--out', default='out/api/plan.json')
    ap.add_argument('--report', default='out/pipeline_report.md')
    ap.add_argument('--mode', default='parsed', choices=['parsed', 'demo'])
    a = ap.parse_args()

    missing = [f for f in a.files if not os.path.exists(f)]
    if missing:
        sys.exit('找不到文件：%s' % ', '.join(missing))

    api, cur, comp, fmt = ingest.ingest_many(
        a.files, a.ocr_cache, source_mode=a.mode)

    for p in (a.out, a.report):
        os.makedirs(os.path.dirname(os.path.abspath(p)) or '.', exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(api, f, ensure_ascii=False, indent=2)
    write_report(a.report, [os.path.basename(x) for x in a.files], api, comp, fmt)

    print('输入    %s' % '、'.join(os.path.basename(x) for x in a.files))
    print('格式    %s（文字层=%s，OCR=%s）'
          % (fmt.get('format'), fmt.get('text_layer'), bool(fmt.get('ocr_used'))))
    print('课程    %d 门 / %d 个课程组' % (len(api['courses']), len(api['groups'])))
    print('学分    必修 %s｜选修池 %s｜毕业要求 %s'
          % (api['credit_summary']['parsed_credits'],
             api['credit_summary']['elective_pool_credits'],
             api['credit_summary']['graduation_target_credits']))
    print('完整度  %s（%d%%）  parse_status=%s  http=%d'
          % (comp['level'], comp['score'], api['parse_status'],
             to_api_v1.http_status(api)))
    for c in comp['checks']:
        print('   %s %-22s %s' % ('✓' if c['ok'] else '✗', c['key'], c['detail']))
    for al in comp['alerts']:
        print('   [%s] %s' % (al['severity'], al['message']))
        print('        → %s' % al['user_action'])
    print('写出    %s' % a.out)
    print('报告    %s' % a.report)
    return 0 if comp['level'] != 'failed' else 1


if __name__ == '__main__':
    sys.exit(main())
