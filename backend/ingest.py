#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一入库：识别格式 → 选适配器 → 解析 → 完整度评估 → 报警 → 出 API 响应。

支持的输入（优先级从高到低，也就是"最好识别"的顺序）：
  1. .docx / .doc   Word 原件          —— 有文字层 + 真实表格结构
  2. .pdf           含文字层的 PDF      —— 有字，但表格要按坐标还原
  3. .pdf           转曲/扫描 PDF       —— 无文字层，必须先栅格化再识别
  4. .png/.jpg…     图片                —— 无版面信息，只能靠识别

没有文字层的文件不会静默失败：会产出 OCR 任务清单 + 完整性报警 +
"请改传哪种文件"的明确建议。
"""
import argparse
import csv
import json
import os
import sys

import curriculum_parser as cp
import to_api_v1

IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}

# 识别可靠性排序（1 最好）。这是给用户看的话术，也是我们自己的实测结论：
#   .doc 样本：40/40 门课、学分逐级核平；
#   无文字层 PDF：0 个字体对象，任何提取库都返回空。
PRIORITY = [
    ('docx', 'Word 原件（.docx）', '有文字层和真实表格，字段最全，推荐首选'),
    ('word97', 'Word 原件（.doc）', '同上；旧格式，另存为 .docx 后更稳'),
    ('pdf_text', '含文字层的 PDF', '有字，但表格靠坐标还原，合并单元格/跨页可能丢行'),
    ('pdf_vector', '转曲或扫描 PDF', '没有文字层，必须先转图识别，准确率最低'),
    ('image', '图片（截图/照片）', '没有版面结构，只能靠识别，不建议'),
]


# ---------------------------------------------------------------- 格式探测
def detect(path):
    low = path.lower()
    ext = os.path.splitext(low)[1]
    if ext == '.docx':
        return {'format': 'docx', 'text_layer': True, 'pages': None, 'ocr_required': False}
    if ext == '.doc':
        return {'format': 'word97', 'text_layer': True, 'pages': None, 'ocr_required': False}
    if ext == '.pdf':
        import pdf_adapter as pa
        doc = pa._Doc(path)
        n_font = sum(1 for k, (d, r) in doc.objs.items() if b'/Font' in d)
        ops = 0
        import re
        for p in doc.pages():
            pd = doc.objs[p][0]
            m = re.search(rb'/Contents\s+(\d+)\s+\d+\s+R', pd)
            if m:
                c = doc.stream(int(m.group(1))) or b''
                ops += c.count(b'BT') + c.count(b'Tj') + c.count(b'TJ')
        text_layer = n_font > 0 and ops > 0
        return {'format': 'pdf_text' if text_layer else 'pdf_vector',
                'text_layer': text_layer, 'pages': len(doc.pages()),
                'fonts': n_font, 'text_ops': ops,
                'ocr_required': not text_layer}
    if ext in IMAGE_EXT:
        return {'format': 'image', 'text_layer': False, 'pages': 1, 'ocr_required': True}
    raise SystemExit('不支持的文件类型：%s' % (ext or '(无扩展名)'))


# ---------------------------------------------------------------- 完整度
REQUIRED_FIELDS = (('name', '课程名'), ('credits', '学分'), ('terms', '修读学期'), ('code', '课程编号'))


def assess(cur, fmt):
    courses = cur.get('courses') or []
    groups = [g for m in (cur.get('modules') or []) for g in (m.get('groups') or [])]
    issues = cur.get('issues') or []
    errors = [i for i in issues if i['level'] == 'error']
    n = len(courses)

    checks = []
    checks.append({'key': 'courses_found', 'ok': n > 0,
                   'detail': '识别到 %d 门课程' % n})
    cov = {}
    for f, label in REQUIRED_FIELDS:
        hit = sum(1 for c in courses if c.get(f) not in (None, '', []))
        cov[f] = (hit, n)
    fields_ok = n > 0 and cov['name'][0] == n and cov['credits'][0] >= max(1, int(n * 0.9))
    checks.append({'key': 'fields_complete', 'ok': fields_ok,
                   'detail': '；'.join('%s %d/%d' % (label, cov[f][0], n)
                                      for f, label in REQUIRED_FIELDS)})

    has_target = (cur.get('meta') or {}).get('total_credits') is not None
    recon = next((i for i in issues if i['code'] == 'TOTAL_SUM'), None)
    reconciled = bool(recon and recon['level'] == 'info' and has_target)
    checks.append({'key': 'credit_target_present', 'ok': has_target,
                   'detail': ('毕业总学分 %s' % cur['meta']['total_credits']) if has_target
                   else '文档未声明毕业总学分'})
    checks.append({'key': 'credit_reconciled', 'ok': reconciled,
                   'detail': recon['message'] if recon else
                   ('已声明但未核平' if has_target else '无总学分可比对，无法判断是否完整')})

    groups_ok = bool(groups) and all(
        (g.get('credits_required') is not None) or (g.get('computed_credits') is not None)
        for g in groups)
    checks.append({'key': 'groups_complete', 'ok': groups_ok,
                   'detail': '识别到 %d 个课程组' % len(groups)})

    passed = sum(1 for c in checks if c['ok'])
    score = round(100.0 * passed / len(checks), 0)
    if n == 0:
        level = 'failed'
    elif all(c['ok'] for c in checks) and not errors:
        level = 'full'
    else:
        level = 'partial'

    alerts = []

    def alert(code, severity, message, action):
        alerts.append({'code': code, 'severity': severity,
                       'message': message, 'user_action': action})

    best = PRIORITY[0]
    if fmt.get('format') in ('pdf_vector', 'image') and not fmt.get('ocr_used'):
        alert('NO_TEXT_LAYER', 'high',
              '这份文件没有文字层（%s），无法直接读取内容。'
              % ('PDF 文字已转曲' if fmt['format'] == 'pdf_vector' else '这是图片'),
              '请优先上传 Word 原件（.docx）；若只能给 PDF，请在 Word/Excel 里用「另存为 PDF」，不要扫描或截图。')
    elif fmt.get('format') in ('pdf_vector', 'image') and fmt.get('ocr_used'):
        alert('OCR_USED', 'medium',
              '这份文件没有文字层，当前结果由图像识别得到，学分/学期/课程名需抽查。',
              '建议改传 Word 原件核对；确认无误后可在前端标记为已核对。')
    if n == 0:
        alert('NO_COURSES', 'high', '没有识别出任何课程。',
              '换用 Word 原件（.docx）重新上传；不要上传图片或扫描件。')
    if fmt.get('render_ok') is False and n == 0:
        alert('RENDER_DEPS_MISSING', 'high',
              '这台机器缺少 numpy/Pillow，无法把 PDF 转成图片，因此无法识别这份文件。',
              '可直接上传 Word 原件（.docx），它在零依赖下就能解析；或安装 numpy 与 Pillow 后再试。')
    if not fields_ok and n > 0:
        alert('FIELDS_INCOMPLETE', 'medium',
              '部分课程缺少关键字段（%s）。' % checks[1]['detail'],
              '请上传版式更规整的原始文件；或在前端逐条补充后再生成计划。')
    if not has_target and n > 0:
        alert('NO_TOTAL_CREDITS', 'medium',
              '文档没有提供毕业总学分，无法判断是否读全（可能只上传了部分文件）。',
              '请上传完整培养方案（含“毕业学分要求”页）或 Word 原件；'
              '若这是按课程性质拆分的单份明细，请把其余文件一并上传。')
    elif has_target and not reconciled:
        alert('CREDIT_NOT_RECONCILED', 'high',
              '学分无法与文档声明值核平，说明有课程或课程组未被完整识别。',
              '请上传同一份方案的 Word 原件（.docx）复核；当前结果请勿直接用于判断毕业进度。')
    if not groups_ok and n > 0:
        alert('GROUPS_INCOMPLETE', 'medium', '课程组要求未完整识别。',
              '上传含完整“模块/课程组学分要求”的原件，或由资料同学补充组要求。')

    return {
        'level': level,
        'score': score,
        'checks': checks,
        'coverage': {f: {'hit': cov[f][0], 'total': n} for f, _ in REQUIRED_FIELDS},
        'alerts': alerts,
        'recommended_upload': {
            'format': best[0],
            'label': best[1],
            'reason': best[2],
            'rank': [{'format': f, 'label': l, 'note': note} for f, l, note in PRIORITY],
        },
    }


# ---------------------------------------------------------------- 无文字层分支
def prepare_ocr(path, fmt, out_dir):
    """把 PDF/图片转成可识别的图，产出一份 OCR 任务清单。
    没有 numpy/Pillow 时不崩，降级为"只登记任务"，由上游报警。"""
    os.makedirs(out_dir, exist_ok=True)
    pages = []
    note = None
    base = os.path.splitext(os.path.basename(path))[0]
    if fmt['format'] == 'pdf_vector':
        try:
            import pdf_raster
        except ImportError as e:
            note = 'MISSING_RENDER_DEPS: %s（未安装 numpy/Pillow，无法把 PDF 转成图片）' % e
        else:
            for i in range(fmt.get('pages') or 1):
                out = os.path.join(out_dir, '%s_p%d.png' % (base, i + 1))
                pdf_raster.render(path, out, 3.0, page_index=i)
                pages.append(out)
    else:
        pages.append(path)
    manifest = {
        'source': path,
        'pages': pages,
        'note': note,
        'schema': {
            'columns': ['group', 'code', 'name', 'nature', 'attr',
                        'hours', 'credits', 'status', 'earned', 'term'],
            'note': '逐页识别后用 assemble_course_list 装配；本仓库的 OCR 缓存就是这个格式的 CSV',
        },
    }
    mpath = os.path.join(out_dir, base + '.ocr_job.json')
    open(mpath, 'w', encoding='utf-8').write(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest, mpath


def parse_with_cache(csv_path, source_name):
    import assemble_course_list as acl
    rows = acl.load(csv_path)
    meta = {
        'source': 'ocr_cache',
        'major_name': None,
        'total_credits': None,
        'note': '由图像识别缓存装配（%s）' % source_name,
    }
    return acl.build(rows, meta)


# ---------------------------------------------------------------- 主流程
def _parse_one(path, fmt, ocr_cache=None):
    if fmt['format'] in ('docx', 'word97', 'pdf_text'):
        return cp.to_json(cp.build(path))
    manifest, mpath = prepare_ocr(path, fmt, 'out/render')
    if (manifest.get('note') or '').startswith('MISSING_RENDER_DEPS'):
        fmt['render_ok'] = False
        fmt['render_note'] = manifest['note']
    if ocr_cache:
        fmt['ocr_used'] = True
        fmt['ocr_job'] = mpath
        return parse_with_cache(ocr_cache, os.path.basename(path))
    fmt['ocr_job'] = mpath
    return {'meta': {}, 'modules': [], 'courses': [],
            'issues': [{'level': 'error', 'code': 'OCR_REQUIRED',
                        'message': '没有文字层，已生成识别任务：%s' % mpath}]}


def merge_curricula(parts):
    """把同一份方案被拆开的多个文件合并成一份。
    parts: [(filename, curriculum)]；同 (课程名, 学分, 课程组) 视为重复。"""
    merged = {'meta': {}, 'modules': [], 'courses': [], 'issues': []}
    seen = set()
    seq = 0
    for fname, cur in parts:
        for k, v in (cur.get('meta') or {}).items():
            if v is not None and merged['meta'].get(k) is None:
                merged['meta'][k] = v
        for m in cur.get('modules') or []:
            tm = next((x for x in merged['modules'] if x['name'] == m['name']), None)
            if tm is None:
                tm = {'id': 'M%d' % (len(merged['modules']) + 1), 'name': m['name'],
                      'credits_required': m.get('credits_required'),
                      'role': m.get('role'), 'groups': []}
                merged['modules'].append(tm)
            for g in m.get('groups') or []:
                tg = next((x for x in tm['groups'] if x['name'] == g['name']), None)
                if tg is None:
                    tg = {'id': '%s.G%d' % (tm['id'], len(tm['groups']) + 1),
                          'name': g['name'], 'credits_required': g.get('credits_required'),
                          'computed_credits': 0, 'subgroups': []}
                    tm['groups'].append(tg)
                for s in g.get('subgroups') or []:
                    ts = next((x for x in tg['subgroups'] if x['name'] == s['name']), None)
                    if ts is None:
                        ts = {'name': s['name'],
                              'credits_required': s.get('credits_required'), 'courses': []}
                        tg['subgroups'].append(ts)
                    for c in s.get('courses') or []:
                        key = (c.get('name'), c.get('credits'), g['name'])
                        if key in seen:
                            continue
                        seen.add(key)
                        seq += 1
                        cc = dict(c)
                        cc['id'] = 'C%03d' % seq
                        cc['source_file'] = fname
                        ts['courses'].append(cc)
                        cc2 = dict(cc)
                        cc2['module'] = m['name']
                        cc2['group'] = g['name']
                        if s['name'] != '默认组':
                            cc2['subgroup'] = s['name']
                        merged['courses'].append(cc2)
        merged['issues'].extend(cur.get('issues') or [])

    # 重算各级学分合计
    for m in merged['modules']:
        total = 0.0
        for g in m['groups']:
            gsum = sum(c['credits'] for s in g['subgroups'] for c in s['courses'])
            g['computed_credits'] = round(gsum, 2)
            total += gsum
        m['computed_credits'] = round(total, 2)

    target = merged['meta'].get('total_credits')
    top = [m for m in merged['modules'] if m.get('role') != 'practice_breakdown']
    tracks = sorted({k for m in top for g in m['groups']
                     if isinstance(g.get('credits_required'), dict)
                     for k in g['credits_required']})
    if target and tracks:
        for t in tracks:
            s = 0.0
            for m in top:
                for g in m['groups']:
                    req = g.get('credits_required')
                    s += (req.get(t) or 0) if isinstance(req, dict) else (req or 0)
            ok = abs(s - target) < 0.01
            merged['issues'].append({
                'level': 'info' if ok else 'error', 'code': 'TOTAL_SUM',
                'message': '[%s] 模块合计 %.2f %s 声明总学分 %.2f'
                           % (t, s, '=' if ok else '≠', target)})
    elif target:
        s = round(sum((m.get('credits_required') or 0) for m in top
                      if isinstance(m.get('credits_required'), (int, float))), 2)
        ok = abs(s - target) < 0.01
        merged['issues'].append({
            'level': 'info' if ok else 'error', 'code': 'TOTAL_SUM',
            'message': '模块合计 %.2f %s 声明总学分 %.2f' % (s, '=' if ok else '≠', target)})
    return merged


def ingest(path, ocr_cache=None, plan_id='plan_demo_001', source_mode='parsed',
           workdir='out/render'):
    api, cur, comp, fmt = ingest_many([path], ocr_cache, plan_id, source_mode, workdir)
    return api, cur, comp, fmt


def ingest_many(paths, ocr_cache=None, plan_id='plan_demo_001', source_mode='parsed',
                workdir='out/render', names=None):
    """多文件：同一份方案被拆成多个文件时合并成一份 plan。
    names 用于保留用户看到的原始文件名（paths 可能是临时文件）。"""
    names = names or [os.path.basename(p) for p in paths]
    parsed, fmts = [], []
    for i, p in enumerate(paths):
        fmt = detect(p)
        fmts.append(fmt)
        parsed.append((names[i], _parse_one(p, fmt, ocr_cache)))

    if len(parsed) == 1:
        cur = parsed[0][1]
        fmt = fmts[0]
    else:
        cur = merge_curricula(parsed)
        fmt = {
            'format': '+'.join(dict.fromkeys(f['format'] for f in fmts)),
            'text_layer': all(f['text_layer'] for f in fmts),
            'ocr_used': any(f.get('ocr_used') for f in fmts),
            'render_ok': all(f.get('render_ok', True) for f in fmts),
            'files': [{'name': names[i], 'format': f['format'],
                       'text_layer': f['text_layer']}
                      for i, f in enumerate(fmts)],
        }

    comp = assess(cur, fmt)
    api = to_api_v1.convert(cur, plan_id=plan_id, file_name=names[0],
                            source_mode=source_mode, format_info=fmt, completeness=comp)
    if len(parsed) > 1:
        api['source']['file_name'] = '%s 等 %d 个文件' % (names[0], len(names))
    return api, cur, comp, fmt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--ocr-cache', help='无文字层文件的识别结果 CSV')
    ap.add_argument('--out', help='把 API 响应写到这个 JSON')
    ap.add_argument('--plan-id', default='plan_demo_001')
    ap.add_argument('--mode', default='parsed', choices=['parsed', 'demo'])
    a = ap.parse_args()

    api, cur, comp, fmt = ingest(a.file, a.ocr_cache, a.plan_id, a.mode)
    text = json.dumps(api, ensure_ascii=False, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, 'w', encoding='utf-8').write(text)

    print('文件      %s' % os.path.basename(a.file))
    print('格式      %s（文字层=%s，OCR=%s）' % (fmt['format'], fmt['text_layer'], bool(fmt.get('ocr_used'))))
    print('课程      %d 门 / 课程组 %d 个' % (len(api['courses']), len(api['groups'])))
    print('学分      必修 %.2f｜选修池 %.2f｜毕业要求 %s'
          % (api['credit_summary']['parsed_credits'],
             api['credit_summary']['elective_pool_credits'],
             api['credit_summary']['graduation_target_credits']))
    print('完整度    %s（%d%%）  parse_status=%s  http=%d'
          % (comp['level'], comp['score'], api['parse_status'], to_api_v1.http_status(api)))
    for c in comp['checks']:
        print('   %s %s  %s' % ('✓' if c['ok'] else '✗', c['key'].ljust(18), c['detail']))
    if comp['alerts']:
        print('报警')
        for al in comp['alerts']:
            print('   [%s] %s\n         → %s' % (al['severity'], al['message'], al['user_action']))
    print('建议上传  %s —— %s' % (comp['recommended_upload']['label'],
                                comp['recommended_upload']['reason']))
    if a.out:
        print('已写出    %s' % a.out)


if __name__ == '__main__':
    main()
