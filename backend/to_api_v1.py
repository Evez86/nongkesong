#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把内部 curriculum.json 映射成 PROJECT_HANDOFF.md §8.3 的
POST /api/v1/training-plans 响应体。

契约扩展（已确认走"新增字段"）：
  courses[].terms     原始学期标记（term 只放 1-8 的整数，兼容旧前端）
  courses[].group     所属课程组
  courses[].track     植物模块 / 动物模块 / null
  groups[]            组级要求与规则（§7.2 要求"各类别要求分别展示"）
  credit_summary.elective_pool_credits   选修课程池大小（不是要求学分）
  completeness        解析完整度 + 报警 + 建议上传格式
"""
import json
import re
import sys

TERM_RE = re.compile(r'^(\d)\s*[秋春夏]$')
TERM_CN_RE = re.compile(r'第\s*(\d+)\s*学期')


def parse_term(course):
    """返回 (term_int_1_8 | None, raw_list)

    培养方案里的“N秋/N春”是**学年制**写法：N 是学年，不是学期。
      1秋→1 1春→2 2秋→3 2春→4 3秋→5 3春→6 4秋→7 4春→8
    依据：文档中“毕业设计 4春”排在最后、“机械设计基础课程设计 3春”在其前一学年。
    纯数字（如教务系统导出的 1~11）按学期理解，超过 8 的留在 terms 里并报警。
    """
    raws = list(course.get('terms') or [])
    if course.get('term_raw'):
        raws.append(str(course['term_raw']))
    for raw in raws:
        raw = str(raw).strip()
        m = TERM_CN_RE.search(raw)
        if m:
            n = int(m.group(1))
            return (n if 1 <= n <= 8 else None), raws
        m = TERM_RE.match(raw)
        if m:
            year = int(m.group(1))
            season = raw[-1]
            term = (year - 1) * 2 + (1 if season == '秋' else 2)
            return (term if 1 <= term <= 8 else None), raws
        if raw.isdigit():
            n = int(raw)
            return (n if 1 <= n <= 8 else None), raws
    return None, raws


def category_of(course, module_name):
    if '实践' in (module_name or ''):
        return 'practice'
    t = (course.get('type') or '').strip()
    raw = (course.get('type_raw') or '') + (course.get('nature_raw') or '')
    if '选修' in raw or t == 'elective':
        return 'elective'
    # module_group（工程模块/植物模块组）是"必修但可置换"，按必修计，
    # 具体差异由 courses[].track 与 groups[].rule 表达
    if t == 'required' or t == 'module_group' or '必修' in raw:
        return 'required'
    return 'other'


def group_rule(g):
    subs = g.get('subgroups') or []
    courses = [c for s in subs for c in (s.get('courses') or [])]
    if not courses:
        return 'unknown'
    if all((c.get('type') == 'required') or ('必修' in (c.get('type_raw') or '')
                                            + (c.get('nature_raw') or '')) for c in courses):
        return 'all_of'
    if '选修' in (g.get('name') or ''):
        return 'candidate_pool'
    return 'credits'


def convert(cur, *, plan_id='plan_demo_001', file_name=None, source_mode='parsed',
            format_info=None, completeness=None):
    meta = cur.get('meta') or {}
    modules = cur.get('modules') or []
    courses_out, groups_out, warnings = [], [], []
    seq = 0
    bad_terms = set()

    for m in modules:
        for g in m.get('groups') or []:
            rule = group_rule(g)
            groups_out.append({
                'name': g.get('name'),
                'module': m.get('name'),
                'rule': rule,
                'credits_required': g.get('credits_required'),
                'computed_credits': g.get('computed_credits'),
                'course_count': sum(len(s.get('courses') or []) for s in g.get('subgroups') or []),
                'practice_credits': g.get('practice_credits'),
            })
            for s in g.get('subgroups') or []:
                for c in s.get('courses') or []:
                    seq += 1
                    term, raw_terms = parse_term(c)
                    if term is None and raw_terms:
                        bad_terms.update(raw_terms)
                    courses_out.append({
                        'id': c.get('id') or 'course_%03d' % seq,
                        'code': c.get('code'),
                        'name': c.get('name'),
                        'term': term,
                        'terms': raw_terms or None,
                        'category': category_of(c, m.get('name')),
                        'group': g.get('name'),
                        'track': c.get('track'),
                        'credits': c.get('credits'),
                        'source_ref': c.get('source') or None,
                    })

    required = sum(c['credits'] or 0 for c in courses_out if c['category'] == 'required')
    pool = sum(c['credits'] or 0 for c in courses_out if c['category'] == 'elective')
    practice = sum(c['credits'] or 0 for c in courses_out if c['category'] == 'practice')

    for code, msg in [(i['code'], i['message'])
                      for i in (cur.get('issues') or [])
                      if i['level'] in ('error', 'warning')]:
        warnings.append({'code': code, 'message': msg})
    if bad_terms:
        warnings.append({
            'code': 'TERM_OUT_OF_RANGE',
            'message': '有学期标记超出 1-8（%s），已保留在 courses[].terms，未写入 term'
                       % '、'.join(sorted(bad_terms)[:5])})

    fmt = format_info or {}
    if fmt.get('text_layer') is False:
        warnings.insert(0, {
            'code': 'NO_TEXT_LAYER',
            'message': '该文件没有文字层（文字已转为图形），只能靠图像识别，字段准确率低于可提取文字的文件。',
            'user_action': '请优先上传 Word 原件（.docx / .doc）；若只能给 PDF，请用 Word「另存为 PDF」而不是「打印成图片」。'})
    if fmt.get('ocr_used'):
        warnings.insert(0, {
            'code': 'OCR_USED',
            'message': '本次结果由图像识别得到，学分、学期、课程名请对照原文抽查。',
            'user_action': '核对高亮字段；确认无误后可在前端标记为已确认。'})

    comp = completeness or {}
    status = 'complete' if comp.get('level') == 'full' else 'partial'

    return {
        'plan_id': plan_id,
        'source': {
            'mode': source_mode,
            'file_name': file_name,
            'format': fmt.get('format'),
            'text_layer': fmt.get('text_layer'),
            'ocr_used': bool(fmt.get('ocr_used')),
            'files': fmt.get('files'),
        },
        'program_name': meta.get('major_name') or meta.get('program_name'),
        'cohort': None,
        'parse_status': status,
        'courses': courses_out,
        'groups': groups_out,
        'credit_summary': {
            'parsed_credits': round(required, 2),
            'elective_pool_credits': round(pool, 2),
            'practice_credits': round(practice, 2),
            'graduation_target_credits': meta.get('total_credits'),
        },
        'warnings': warnings,
        'completeness': comp or None,
    }


def http_status(api):
    """契约 §8.3：“整份无法解析时返回错误”。failed ⇔ 422，其余 200。
    FastAPI 侧据此选择 200 还是 422 + error 信封。"""
    comp = api.get('completeness') or {}
    return 422 if comp.get('level') == 'failed' else 200


if __name__ == '__main__':
    cur = json.load(open(sys.argv[1], encoding='utf-8'))
    out = convert(cur, file_name=sys.argv[2] if len(sys.argv) > 2 else None)
    dest = sys.argv[3] if len(sys.argv) > 3 else None
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if dest:
        open(dest, 'w', encoding='utf-8').write(text)
        print('wrote', dest, '| courses', len(out['courses']), '| status', out['parse_status'])
    else:
        print(text)
