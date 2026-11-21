#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
培养方案解析引擎 v0.1
=====================
输入：.doc / .docx 的培养方案（同一套 IR，PDF 适配器按相同接口扩展）
输出：curriculum.json（统一 schema）+ parse_report.md（校验报告）

设计原则（对应产品要求“不能写死某一所学校”）：
  1. 抽取层不认识课程，只吐"段落 + 表格单元格流"；
  2. 行还原靠"学分锚点 + 邻居字段形态"，不依赖固定列序；
  3. 组与规则靠标题语义（"XX：N学分" / "至少N学分" / "选N门"）推断；
  4. 一切数字都要和声明值对账，对不上的进 issues，不静默修正。
"""
import json
import re
import struct
import sys
import zipfile
from xml.etree import ElementTree as ET

CELL_MARK = '\x07'
PARA_MARK = '\n'


# ============================================================ 抽取层
def _ole_streams(path):
    b = open(path, 'rb').read()
    if b[:8] != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        raise ValueError('not an OLE2 file')
    ssz = 1 << struct.unpack_from('<H', b, 0x1E)[0]
    mssz = 1 << struct.unpack_from('<H', b, 0x20)[0]
    n_fat = struct.unpack_from('<I', b, 0x2C)[0]
    dir_start = struct.unpack_from('<I', b, 0x30)[0]
    mini_cutoff = struct.unpack_from('<I', b, 0x38)[0]
    minifat_start = struct.unpack_from('<I', b, 0x3C)[0]
    n_minifat = struct.unpack_from('<I', b, 0x40)[0]
    difat_start = struct.unpack_from('<I', b, 0x44)[0]
    n_difat = struct.unpack_from('<I', b, 0x48)[0]

    def sector(i):
        off = 512 + i * ssz
        return b[off:off + ssz]

    difat = list(struct.unpack_from('<109I', b, 0x4C))
    sec = difat_start
    for _ in range(n_difat):
        if sec >= 0xFFFFFFFA:
            break
        vals = struct.unpack_from('<%dI' % (ssz // 4), sector(sec), 0)
        difat.extend(vals[:-1])
        sec = vals[-1]
    difat = [d for d in difat if d < 0xFFFFFFFA][:n_fat]

    fat = []
    for d in difat:
        fat.extend(struct.unpack_from('<%dI' % (ssz // 4), sector(d), 0))

    def chain(start):
        out, s = [], start
        while s < 0xFFFFFFFA and len(out) < 2_000_000:
            out.append(s)
            s = fat[s] if s < len(fat) else 0xFFFFFFFE
        return out

    def stream(start, size):
        return b''.join(sector(s) for s in chain(start))[:size]

    dirdata = stream(dir_start, 1 << 30)
    entries = []
    for i in range(0, len(dirdata) - 127, 128):
        e = dirdata[i:i + 128]
        nlen = struct.unpack_from('<H', e, 0x40)[0]
        name = e[:max(0, nlen - 2)].decode('utf-16-le', 'ignore')
        entries.append((name, e[0x42],
                        struct.unpack_from('<I', e, 0x74)[0],
                        struct.unpack_from('<I', e, 0x78)[0]))
    root = next(e for e in entries if e[1] == 5)
    mini_stream = stream(root[2], root[3])
    minifat = []
    if n_minifat:
        mf = b''.join(sector(s) for s in chain(minifat_start))
        minifat = list(struct.unpack_from('<%dI' % (len(mf) // 4), mf, 0))

    def mini_chain(start):
        out, s = [], start
        while s < 0xFFFFFFFA:
            out.append(s)
            s = minifat[s]
        return out

    def get(name):
        for n, t, st, sz in entries:
            if n == name and t == 2:
                if sz < mini_cutoff:
                    data = b''.join(mini_stream[s * mssz:(s + 1) * mssz] for s in mini_chain(st))
                    return data[:sz]
                return stream(st, sz)
        return None

    return get


def _doc_text(path):
    """Word 97-2003：按 piece table 还原正文，\\x07 保留单元格标记。"""
    get = _ole_streams(path)
    wd = get('WordDocument')
    flags = struct.unpack_from('<H', wd, 0x0A)[0]
    tbl = get('1Table' if (flags & 0x0200) else '0Table') or get('1Table') or get('0Table')
    fcClx = struct.unpack_from('<I', wd, 0x01A2)[0]
    lcbClx = struct.unpack_from('<I', wd, 0x01A6)[0]
    clx = tbl[fcClx:fcClx + lcbClx]
    i = 0
    plc = None
    while i < len(clx):
        if clx[i] == 0x01:
            i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
        elif clx[i] == 0x02:
            lcb = struct.unpack_from('<I', clx, i + 1)[0]
            plc = clx[i + 5:i + 5 + lcb]
            break
        else:
            i += 1
    if plc is None:
        raise ValueError('no piece table')
    n = (len(plc) - 4) // 12
    cps = list(struct.unpack_from('<%dI' % (n + 1), plc, 0))
    pcd_off = (n + 1) * 4
    out = []
    for k in range(n):
        fc = struct.unpack_from('<I', plc, pcd_off + k * 8 + 2)[0]
        comp = bool(fc & 0x40000000)
        off = (fc & 0x3FFFFFFF) // 2 if comp else fc
        ln = cps[k + 1] - cps[k]
        if comp:
            out.append(wd[off:off + ln].decode('cp1252', 'replace'))
        else:
            out.append(wd[off:off + ln * 2].decode('utf-16-le', 'replace'))
    return ''.join(out).replace('\r', '\n')


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _docx_blocks(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml')
    root = ET.fromstring(xml)
    body = root.find(W + 'body')

    def para_text(p):
        return ''.join(t.text or '' for t in p.iter(W + 't'))

    blocks = []
    for el in body:
        if el.tag == W + 'p':
            txt = para_text(el).strip()
            if txt:
                blocks.append(('p', txt))
        elif el.tag == W + 'tbl':
            rows = []
            for tr in el.findall(W + 'tr'):
                rows.append([para_text(tc).strip() for tc in tr.findall(W + 'tc')])
            blocks.append(('t', rows))
    return blocks


def _doc_blocks(text):
    """\\x07 结束一个单元格：token 的 parts[0] 是该单元格内容（可能本身是标题），
    parts[1:] 是同一单元格里的后续段落。文档顺序 = 先单元格，再段落。"""
    blocks = []
    for tok in text.split(CELL_MARK):
        parts = tok.split(PARA_MARK)
        cell = parts[0].strip()
        blocks.append(('c', cell))          # 保留空单元格，维持表格列位对齐
        for line in parts[1:]:
            line = line.replace('\x02', '').replace('#', '').strip()
            if line:
                blocks.append(('p', line))
    return blocks


def load_blocks(path):
    low = path.lower()
    if low.endswith('.doc'):
        return _doc_blocks(_doc_text(path))
    if low.endswith('.docx'):
        return _docx_blocks(path)
    if low.endswith('.pdf'):
        import pdf_adapter
        return pdf_adapter.load_blocks(path)
    raise ValueError('unsupported format: %s' % path)


# ============================================================ 归一化
TYPE_ALIASES = [
    (r'必修', 'required'),
    (r'^选修$|限选|任选|方向', 'elective'),
    (r'模块组?$|模块$', 'module_group'),
]
TERM_RE = re.compile(r'^(\d)(春|夏|秋)(\d)?(春|夏|秋)?$')
HOURS_RE = re.compile(r'^(\d+(?:\.\d+)?)(周)?(?:\+(\d+(?:\.\d+)?)(周)?)?$')
CREDIT_RE = re.compile(r'^\d+(?:\.\d+)?$')
UNIT_RE = re.compile(r'学院|学校|外教|大学|中心|教务|学部|系$')
NUM_HEAD = re.compile(r'^[（(](\d+)[）)]')


def norm_type(raw):
    raw = (raw or '').strip()
    if not raw:
        return None
    for pat, val in TYPE_ALIASES:
        if re.search(pat, raw):
            return val
    return 'other'


def parse_credits(s):
    m = re.match(r'\s*(\d+(?:\.\d+)?)', s or '')
    return float(m.group(1)) if m else None


CN_DIGITS = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def cn2int(s):
    if s.isdigit():
        return int(s)
    if s in CN_DIGITS:
        return CN_DIGITS[s]
    if s.startswith('十'):
        return 10 + CN_DIGITS.get(s[1:], 0)
    if '十' in s:
        a, _, b = s.partition('十')
        return CN_DIGITS.get(a, 0) * 10 + CN_DIGITS.get(b, 0)
    return None


def parse_credit_spec(s):
    """'75.5（植物模块）/78.5（动物模块）' -> {'植物模块':75.5,'动物模块':78.5}"""
    s = re.split(r'[，,]', s or '')[0]          # 只取首句，避免"其中…"干扰
    s = re.split(r'其中', s)[0]
    pairs = re.findall(r'([\d.]+)\s*[（(]([^）)]+)[）)]', s)
    if pairs:
        return {_clean_track(k): float(v) for v, k in pairs}
    v = parse_credits(s)
    return v


def _clean_track(k):
    k = k.replace('模块组', '模块').replace('组', '')
    return k.strip()


def parse_hours(raw):
    raw = (raw or '').strip()
    m = HOURS_RE.match(raw)
    if not m:
        return None
    th = float(m.group(1)) if m.group(1) else 0.0
    pr = float(m.group(3)) if m.group(3) else 0.0
    if m.group(2):
        return {'weeks': th, 'theory': None, 'practice': None}
    return {'theory': th, 'practice': pr}


# ============================================================ 解析器
TOP_MODULES = ('通识教育', '大类平台教育', '专业教育', '实践教育环节')
SKIP_PARA = re.compile(r'^(?:- ?\d+ ?-|\s*)$')


class Parser:
    def __init__(self):
        self.meta = {}
        self.modules = []
        self.issues = []
        self.notes = []
        self.cur_module = None
        self.cur_group = None
        self.cur_sub = None
        self.course_seq = 0
        self.seen_names = {}
        self.last_type = None
        self.all_courses = []
        self.practice_rows = []
        self.orphan_practice = []
        self.practice_group_credits = []

    # ---------- 结构 ----------
    def module(self, name, credits):
        m = {'id': 'M%d' % (len(self.modules) + 1), 'name': name,
             'credits_required': credits, 'groups': []}
        if name == '实践教育环节':
            m['role'] = 'practice_breakdown'   # 与主课程表重叠，只做学分归集
        self.modules.append(m)
        self.cur_module = m
        self.cur_group = None
        self.cur_sub = None
        return m

    def group(self, name, credits):
        g = {'id': '%s.G%d' % (self.cur_module['id'], len(self.cur_module['groups']) + 1),
             'name': name, 'credits_required': credits, 'subgroups': []}
        self.cur_module['groups'].append(g)
        self.cur_group = g
        self.cur_sub = None
        return g

    def subgroup(self, name, credits):
        if self.cur_group is None:
            self.group(name, credits)
            return self.cur_group
        s = {'name': name, 'credits_required': credits, 'courses': []}
        self.cur_group['subgroups'].append(s)
        self.cur_sub = s
        return s

    # ---------- 段落 ----------
    def feed_para(self, line):
        line = line.strip()
        if not line or SKIP_PARA.match(line):
            return
        if line.startswith('注') or line.startswith('说明') or line.startswith('1、') or line.startswith('2、'):
            if self.cur_group is not None:
                self.cur_group.setdefault('notes', []).append(line)
            else:
                self.notes.append(line)
            return

        # 全局元信息
        if '总学分' in line:
            m = re.search(r'(?<!环节)总学分[:：]\s*(\d+(?:\.\d+)?)', line)
            if m and 'total_credits' not in self.meta:
                self.meta['total_credits'] = float(m.group(1))
            m = re.search(r'通识教育学分[:：]\s*(\d+(?:\.\d+)?)', line)
            if m:
                self.meta['general_credits'] = float(m.group(1))
            m = re.search(r'实践教育环节总学分[:：]\s*(\d+(?:\.\d+)?)', line)
            if m:
                self.meta['practice_credits_declared'] = float(m.group(1))
            return
        if '年制本科' in line or '授予学位' in line:
            m = re.search(r'([一二三四五六七八九十\d]+)\s*年制本科', line)
            if m:
                self.meta['duration_years'] = cn2int(m.group(1))
            m = re.search(r'授予学位门类[:：]\s*([^，。;；]*?)学士', line)
            if m:
                self.meta['degree'] = re.sub(r'\s+', '', m.group(1)) + '学士'
            return
        if line.startswith('专业类及专业类代码'):
            m = re.search(r'[:：]\s*(.+)$', line)
            if m:
                self.meta['major_name'] = m.group(1).strip()
            return

        head = NUM_HEAD.match(line)
        m = re.match(r'^(?:（\d+）)?\s*([^：:]{2,30}?)\s*[:：]\s*(.*)$', line)
        if not m:
            return
        name, rest = m.group(1).strip(), m.group(2).strip()
        if name in TOP_MODULES:
            self.module(name, parse_credit_spec(rest))
            return
        if not self.modules:
            return
        # 只有"后面跟学分数"的才是学分标题，排除"专业分流：学生在…"这类正文
        if not re.match(r'^[\d（(]', rest) and '学分' not in rest:
            return
        spec = parse_credit_spec(rest)
        if head:
            self.subgroup(name, spec)
        else:
            self.group(name, spec)

    # ---------- 课程行 ----------
    def try_row(self, cells, i):
        """学分锚点法：以 j 为学分位，向前找 学时/类别/单位/名称，向后找学期。"""
        n = len(cells)
        for j in range(i, min(i + 12, n)):
            if not CREDIT_RE.match(cells[j]):
                continue
            if j - 4 < i or j + 1 >= n:
                continue
            c_hours, c_type, c_unit, c_name = cells[j - 1], cells[j - 2], cells[j - 3], cells[j - 4]
            c_term = cells[j + 1]
            if not HOURS_RE.match(c_hours or ''):
                continue
            if not UNIT_RE.search(c_unit or ''):
                continue
            if not c_name or CREDIT_RE.match(c_name) or len(c_name) > 60:
                continue
            if not (TERM_RE.match(c_term or '') or '不限' in (c_term or '')):
                continue
            if not (c_type or '').strip():          # 合并单元格：类别向上顺延
                c_type = self.last_type or ''
                if not c_type:
                    continue
            code = cells[j - 5] if j - 5 >= i else ''
            code = code.strip() if re.match(r'^\d{6,}$', code.strip() or '') else None
            return j - 5 if code else j - 4, j + 2, {
                'code': code,
                'name': c_name.strip(),
                'unit': c_unit.strip(),
                'type_raw': c_type.strip(),
                'hours_raw': c_hours.strip(),
                'credits': float(cells[j]),
                'term_raw': c_term.strip(),
            }
        return None, None, None

    def feed_cells(self, cells):
        i, n = 0, len(cells)
        while i < n:
            c = cells[i].strip()
            if not c:
                i += 1
                continue
            # 段落混进单元格流（Word 把表后正文并进最后一个单元格）：交回段落解析
            if len(c) > 22 or (('：' in c or ':' in c) and '学分' in c):
                self.feed_para(c)
                i += 1
                continue
            # 单元格内的分组标签："通识实践课：4.5"
            if re.match(r'^[^0-9]{2,40}[:：]\s*[\d.]+\s*学分?$', c) and not UNIT_RE.search(c):
                name, _, spec = c.partition('：' if '：' in c else ':')
                if self.cur_module is not None:
                    self.subgroup(name.strip(), parse_credit_spec(spec))
                i += 1
                continue
            start, end, row = self.try_row(cells, i)
            if row is None:
                i += 1
                continue
            start = max(0, start)
            self.add_course(row)
            i = max(end, i + 1)

    def add_course(self, row):
        if row.get('type_raw'):
            self.last_type = row['type_raw']
        # 实践学分表是对同一批课程的"实践部分"再投影，不新建课程，只挂回主表
        if self.cur_module and self.cur_module.get('role') == 'practice_breakdown':
            self.practice_rows.append(row)
            return
        target = self.cur_sub
        if target is None:
            if self.cur_group is None:
                return
            target = self.cur_group.setdefault('subgroups', [])
            if not target:
                self.cur_group['subgroups'].append({'name': '默认组', 'credits_required': None, 'courses': []})
            target = self.cur_group['subgroups'][-1]
        self.course_seq += 1
        course = {
            'id': 'C%03d' % self.course_seq,
            'code': row['code'],
            'name': row['name'],
            'unit': row['unit'],
            'type': norm_type(row['type_raw']),
            'type_raw': row['type_raw'],
            'hours': parse_hours(row['hours_raw']),
            'hours_raw': row['hours_raw'],
            'credits': row['credits'],
            'terms': [t.strip() for t in re.split(r'(?=\d[春夏秋])', row['term_raw']) if t.strip()],
            'track': _clean_track(row['type_raw']) if norm_type(row['type_raw']) == 'module_group' else None,
        }
        target['courses'].append(course)
        self.all_courses.append(course)
        self.seen_names.setdefault(row['name'], []).append(course)

    # ---------- 实践学分归集 ----------
    def resolve_practice(self):
        """把实践学分表逐行挂回主课程表；名字对不上的单独记，不静默丢弃。"""
        import difflib
        for row in self.practice_rows:
            name = row['name']
            hit = next((c for c in self.all_courses if c['name'] == name), None)
            if hit is None:
                best, ratio = None, 0.0
                for c in self.all_courses:
                    r = difflib.SequenceMatcher(None, c['name'], name).ratio()
                    if r > ratio:
                        best, ratio = c, r
                if ratio >= 0.75:
                    best['practice_credits'] = row['credits']
                    best['practice_match'] = 'fuzzy'
                    self.issues.append({
                        'level': 'warning', 'code': 'PRACTICE_NAME_MISMATCH',
                        'message': '实践表“%s”按相似度 %.2f 匹配到课程表“%s”，请人工确认'
                                   % (name, ratio, best['name']),
                        'courses': [best['id']]})
                    continue
                # 组级别的实践学分（如“思政社会实践课 1.5”无课程行）
                if self.match_group(name, row['credits']):
                    continue
                self.orphan_practice.append(row)
                continue
            hit['practice_credits'] = row['credits']
            hit['practice_match'] = 'exact'
            if row['hours_raw'] and row['hours_raw'] != hit['hours_raw']:
                hit['practice_hours_raw'] = row['hours_raw']

    def match_group(self, name, credits):
        import difflib
        for m in self.modules:
            for g in m['groups']:
                if g['name'] == name:
                    g['practice_credits'] = credits
                    self.practice_group_credits.append({'name': name, 'credits': credits})
                    return True
                for s in g['subgroups']:
                    if s['name'] == name:
                        s['practice_credits'] = credits
                        self.practice_group_credits.append({'name': name, 'credits': credits})
                        return True
        # 近似匹配（如“思政社会实践课”→“思想政治教育社会实践课”）
        best, ratio = None, 0.0
        for m in self.modules:
            for g in m['groups']:
                for s in list(g['subgroups']) + [g]:
                    r = difflib.SequenceMatcher(None, s['name'], name).ratio()
                    if r > ratio:
                        best, ratio = s, r
        if best is not None and ratio >= 0.6:
            best['practice_credits'] = credits
            self.practice_group_credits.append(
                {'name': best['name'], 'credits': credits, 'matched_from': name, 'ratio': round(ratio, 2)})
            return True
        return False

    # ---------- 校验 ----------
    def validate(self):
        issues = []

        def add(level, code, msg, **extra):
            d = {'level': level, 'code': code, 'message': msg}
            d.update(extra)
            issues.append(d)

        tracks = []
        for m in self.modules:
            for g in m['groups']:
                req = g.get('credits_required')
                if isinstance(req, dict):
                    for k in req:
                        if k not in tracks:
                            tracks.append(k)

        def req_of(req, track):
            return req.get(track) if isinstance(req, dict) else req

        def counted(c, t):
            tr = c.get('track')
            return tr is None or tr not in tracks or tr == t

        def sum_tracks(courses):
            if not tracks:
                return round(sum(c['credits'] for c in courses), 2)
            return {t: round(sum(c['credits'] for c in courses if counted(c, t)), 2)
                    for t in tracks}

        def one(v):
            """数值化：分轨字典取首轨（用于只声明单一数值的组）"""
            if isinstance(v, dict):
                return list(v.values())[0] if v else 0.0
            return v

        for m in self.modules:
            for g in m['groups']:
                gcourses = []
                for s in g['subgroups']:
                    cs = sum_tracks(s['courses'])
                    gcourses += s['courses']
                    req = s.get('credits_required')
                    if s['courses']:
                        if isinstance(req, dict):
                            for t, v in req.items():
                                got = cs.get(t)
                                if got is not None and abs(got - v) > 0.01:
                                    add('warning', 'SUBGROUP_SUM',
                                        '%s / %s [%s]：课程合计 %.2f，声明 %.2f'
                                        % (g['name'], s['name'], t, got, v))
                        elif isinstance(req, (int, float)) and abs(one(cs) - req) > 0.01:
                            add('warning', 'SUBGROUP_SUM',
                                '%s / %s：课程合计 %.2f，声明 %.2f'
                                % (g['name'], s['name'], one(cs), req))
                g['computed_credits'] = sum_tracks(gcourses)
                req = g.get('credits_required')
                if isinstance(req, dict):
                    for t, v in req.items():
                        got = g['computed_credits'].get(t)
                        if gcourses and got is not None and abs(got - v) > 0.01:
                            add('warning', 'GROUP_SUM',
                                '%s [%s]：课程合计 %.2f，声明 %.2f' % (g['name'], t, got, v))
                elif isinstance(req, (int, float)) and gcourses and abs(one(g['computed_credits']) - req) > 0.01:
                    add('warning', 'GROUP_SUM',
                        '%s：课程合计 %.2f，声明 %.2f' % (g['name'], one(g['computed_credits']), req))
            if tracks:
                m['computed_credits'] = {
                    t: round(sum(req_of(g.get('credits_required'), t) or 0
                                 for g in m['groups']), 2)
                    for t in tracks}
            else:
                m['computed_credits'] = round(sum(
                    g.get('credits_required') or 0 for g in m['groups']
                    if isinstance(g.get('credits_required'), (int, float))), 2)

        top = [m for m in self.modules if m.get('role') != 'practice_breakdown']
        total = self.meta.get('total_credits')
        if total and top:
            if tracks:
                for t in tracks:
                    s = sum((m['computed_credits'].get(t) or 0) for m in top)
                    ok = abs(s - total) < 0.01
                    add('info' if ok else 'error', 'TOTAL_SUM',
                        '[%s] 模块合计 %.2f %s 声明总学分 %.2f' % (t, s, '=' if ok else '≠', total))
            else:
                s = sum((m['computed_credits'] or 0) for m in top)
                ok = abs(s - total) < 0.01
                add('info' if ok else 'error', 'TOTAL_SUM',
                    '模块合计 %.2f %s 声明总学分 %.2f' % (s, '=' if ok else '≠', total))

        dedup = {}
        for name, cs in self.seen_names.items():
            if len(cs) > 1:
                dedup[name] = cs
        for name, cs in dedup.items():
            views = {c.get('view', 'main') for c in cs}
            if views == {'main'}:
                add('warning', 'DUPLICATE_COURSE',
                    '“%s”出现在多个组，学分会重复计算' % name,
                    courses=[c['id'] for c in cs])
            else:
                add('info', 'PRACTICE_OVERLAP',
                    '“%s”同时出现在课程表与实践学分表（仅归集，不重复计数）' % name,
                    courses=[c['id'] for c in cs])

        # 实践学分核对
        declared_p = self.meta.get('practice_credits_declared')
        covered = round(sum(c.get('practice_credits') or 0 for c in self.all_courses)
                        + sum(g['credits'] for g in self.practice_group_credits), 2)
        pm = next((m for m in self.modules if m.get('role') == 'practice_breakdown'), None)
        declared_mod = pm.get('credits_required') if pm else None
        if declared_mod and declared_p and abs(declared_mod - declared_p) > 0.01:
            add('warning', 'CONFLICTING_DECLARATIONS',
                '实践学分两处声明不一致：“实践教育环节” %.2f vs“毕业学分要求” %.2f'
                % (declared_mod, declared_p))
        target = declared_mod or declared_p
        if target:
            residual = round(target - covered, 2)
            unlisted = None
            if residual > 0.01 and pm:
                numeric_hit = None
                for g in pm['groups']:
                    req = g.get('credits_required')
                    if isinstance(req, dict):
                        continue
                    if not any(s['courses'] for s in g['subgroups']) and req and abs(req - residual) < 0.01:
                        numeric_hit = g['name']
                unlisted = numeric_hit
            msg = '实践学分：已归集 %.2f（课程 %d 门 + 课组 %d 项），声明 %.2f' % (
                covered, len([c for c in self.all_courses if c.get('practice_credits')]),
                len(self.practice_group_credits), target)
            if residual > 0.01:
                msg += '，差额 %.2f%s' % (
                    residual,
                    ' 来自未列明条目的“%s”✓' % unlisted if unlisted else '（需人工确认）')
            elif residual < -0.01:
                msg += '，超出 %.2f（可能重复计数）' % (-residual)
            else:
                msg += ' ✓'
            add('info' if residual <= 0.01 else 'warning', 'PRACTICE_TOTAL', msg)
        for row in self.orphan_practice:
            add('warning', 'PRACTICE_ORPHAN',
                '实践表“%s”（%.2f 学分）在主课程表中找不到对应课程' % (row['name'], row['credits']))

        # 双轨学分一致性
        for m in self.modules:
            for g in m['groups']:
                req = g.get('credits_required')
                if isinstance(req, dict):
                    add('info', 'TRACK_VARIANTS',
                        '%s 学分为分模块设定：%s' % (g['name'], json.dumps(req, ensure_ascii=False)))
        self.issues = issues
        return issues

    def summary(self):
        courses = []
        for m in self.modules:
            for g in m['groups']:
                for s in g['subgroups']:
                    for c in s['courses']:
                        c2 = dict(c)
                        c2['module'] = m['name']
                        c2['group'] = g['name']
                        if s['name'] != '默认组':
                            c2['subgroup'] = s['name']
                        courses.append(c2)
        return {
            'meta': self.meta,
            'course_count': len(courses),
            'practice_rows': len(self.practice_rows),
            'courses': courses,
        }


def build_from_blocks(blocks):
    p = Parser()
    buf = []

    def flush():
        if buf:
            p.feed_cells(buf)
            buf.clear()

    for kind, payload in blocks:
        if kind == 'p':
            flush()
            p.feed_para(payload)
        elif kind == 't':                      # docx：一整张表，按行喂
            flush()
            for row in payload:
                p.feed_cells([str(x) for x in row])
        else:
            buf.append(payload)
    flush()
    p.resolve_practice()
    p.validate()
    return p


def build(path):
    return build_from_blocks(load_blocks(path))


def to_json(p):
    data = p.summary()
    return {
        'schema_version': '0.1',
        'meta': data['meta'],
        'modules': p.modules,
        'courses': data['courses'],
        'issues': p.issues,
    }


if __name__ == '__main__':
    src = sys.argv[1]
    out_json = sys.argv[2]
    parser = build(src)
    payload = to_json(parser)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        'courses': len(payload['courses']),
        'modules': len(payload['modules']),
        'issues': len(payload['issues']),
    }, ensure_ascii=False))
