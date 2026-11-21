#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF 抽取适配器：把 PDF 还原成"行 = 若干单元格"的表格，供 curriculum_parser 复用。
纯标准库：自己解 PDF 对象流、ToUnicode、内容流，按坐标聚类成行列。
"""
import base64
import re
import sys
import zlib


# ------------------------------------------------------------ PDF 基础
def _a85(raw):
    s = raw.strip()
    if s.startswith(b'<~'):
        s = s[2:]
    e = s.find(b'~>')
    if e >= 0:
        s = s[:e]
    s = re.sub(rb'\s', b'', s)
    try:
        return base64.a85decode(s, adobe=False)
    except Exception:
        return b''


def _filters(d):
    m = re.search(rb'/Filter\s*\[(.*?)\]', d, re.S)
    if m:
        return re.findall(rb'/([A-Za-z0-9]+)', m.group(1))
    m = re.search(rb'/Filter\s*/([A-Za-z0-9]+)', d)
    return [m.group(1)] if m else []


def _decode(d, raw):
    out = raw
    for f in _filters(d):
        try:
            if f in (b'ASCII85Decode', b'A85'):
                out = _a85(out)
            elif f == b'FlateDecode':
                out = zlib.decompress(out)
            elif f == b'ASCIIHexDecode':
                out = bytes.fromhex(re.sub(rb'[^0-9A-Fa-f]', b'', out).decode())
            else:
                return None
        except Exception:
            try:
                out = zlib.decompressobj().decompress(out)
            except Exception:
                return None
    return out


def _objects(buf):
    objs = {}
    for m in re.finditer(rb'(?:^|[\r\n>])\s*(\d+)\s+(\d+)\s+obj\b', buf):
        num, start = int(m.group(1)), m.end()
        sidx = buf.find(b'stream', start)
        eidx = buf.find(b'endobj', start)
        if sidx >= 0 and (eidx < 0 or sidx < eidx):
            d = buf[start:sidx]
            s = sidx + 6
            if buf[s:s + 2] == b'\r\n':
                s += 2
            elif buf[s:s + 1] in (b'\n', b'\r'):
                s += 1
            e = buf.find(b'endstream', s)
            objs[num] = (d, buf[s:e if e > 0 else len(buf)])
        else:
            objs[num] = (buf[start:eidx if eidx > 0 else len(buf)], None)
    # 对象流
    extra = {}
    for num, (d, raw) in list(objs.items()):
        if raw is None or b'/ObjStm' not in d:
            continue
        s = _decode(d, raw)
        if not s:
            continue
        mN = re.search(rb'/N\s+(\d+)', d)
        mF = re.search(rb'/First\s+(\d+)', d)
        if not (mN and mF):
            continue
        n, first = int(mN.group(1)), int(mF.group(1))
        head = s[:first].split()
        try:
            pairs = [(int(head[2 * i]), int(head[2 * i + 1])) for i in range(n)]
        except Exception:
            continue
        for i, (onum, off) in enumerate(pairs):
            end = pairs[i + 1][1] + first if i + 1 < len(pairs) else len(s)
            extra.setdefault(onum, (s[first + off:end], None))
    for k, v in extra.items():
        objs.setdefault(k, v)
    return objs


def _cmap(txt):
    mp = {}
    for block in re.findall(rb'beginbfchar(.*?)endbfchar', txt, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
            try:
                mp[int(a, 16)] = bytes.fromhex(b.decode()).decode('utf-16-be', 'ignore')
            except Exception:
                pass
    for block in re.findall(rb'beginbfrange(.*?)endbfrange', txt, re.S):
        for m in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[(.*?)\])',
                             block, re.S):
            lo, hi = int(m.group(1), 16), int(m.group(2), 16)
            if m.group(3):
                bs = bytes.fromhex(m.group(3).decode()).decode('utf-16-be', 'ignore')
                for i in range(min(hi - lo + 1, 5000)):
                    if bs:
                        mp[lo + i] = bs[:-1] + chr(ord(bs[-1]) + i)
            elif m.group(4):
                for i, it in enumerate(re.findall(rb'<([0-9A-Fa-f]+)>', m.group(4))):
                    try:
                        mp[lo + i] = bytes.fromhex(it.decode()).decode('utf-16-be', 'ignore')
                    except Exception:
                        pass
    return mp


class _Doc:
    def __init__(self, path):
        self.objs = _objects(open(path, 'rb').read())

    def stream(self, num):
        e = self.objs.get(num)
        if not e or e[1] is None:
            return None
        return _decode(e[0], e[1])

    def ref(self, dic, key):
        m = re.search(key.encode() + rb'\s+(\d+)\s+\d+\s+R', dic)
        return int(m.group(1)) if m else None

    def font(self, num):
        d = self.objs[num][0]
        tu = self.ref(d, '/ToUnicode')
        mp = _cmap(self.stream(tu)) if tu else {}
        widths, first = {}, 0
        m = re.search(rb'/FirstChar\s+(\d+)', d)
        if m:
            first = int(m.group(1))
        mw = re.search(rb'/Widths\s*\[(.*?)\]', d, re.S)
        if mw:
            for i, v in enumerate(re.findall(rb'[-+]?\d*\.?\d+', mw.group(1))):
                widths[first + i] = float(v) / 1000.0
        return {'cmap': mp, 'widths': widths,
                'two': bool(re.search(rb'/Subtype\s*/Type0', d))}

    def fonts(self, res_dict):
        out = {}
        block = None
        m = re.search(rb'/Font\s*<<(.*?)>>', res_dict, re.S)
        if m:
            block = m.group(1)
        else:
            n = self.ref(res_dict, '/Font')
            if n and n in self.objs:
                block = self.objs[n][0]
        if block:
            for nm, onum in re.findall(rb'/([^\s/<>\[\]()]+)\s+(\d+)\s+\d+\s+R', block):
                if int(onum) in self.objs:
                    out[nm.decode('latin-1')] = self.font(int(onum))
        return out

    def pages(self):
        return sorted(n for n, (d, r) in self.objs.items()
                      if re.search(rb'/Type\s*/Page[^s]', d))


TOKEN = re.compile(rb'/([^\s/<>\[\]()%{}]+)|<<|>>|\[|\]|<([0-9A-Fa-f\s]*)>|(\()|([-+]?\d*\.?\d+)|([A-Za-z\'"*]+)')


def _unescape(b):
    out, i = bytearray(), 0
    simple = {0x6e: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12,
              0x28: 0x28, 0x29: 0x29, 0x5c: 0x5c}
    while i < len(b):
        c = b[i]
        if c == 0x5c and i + 1 < len(b):
            n = b[i + 1]
            if n in simple:
                out.append(simple[n]); i += 2; continue
            if 0x30 <= n <= 0x37:
                m = re.match(rb'[0-7]{1,3}', b[i + 1:i + 4])
                out.append(int(m.group(0), 8) & 0xFF); i += 1 + len(m.group(0)); continue
            i += 2; continue
        out.append(c); i += 1
    return bytes(out)


def _text(raw, font):
    if not font:
        return ''.join(chr(c) for c in raw if 32 <= c < 127), 0.0
    cmap, widths = font['cmap'], font['widths']
    codes = ([(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw) - 1, 2)]
             if font['two'] else list(raw))
    out, adv = [], 0.0
    for c in codes:
        u = cmap.get(c)
        if u is None:
            u = '' if font['two'] else (chr(c) if 32 <= c < 127 else '')
        out.append(u)
        adv += widths.get(c, 0.5)
    return ''.join(out), adv


def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2]


def _items(content, fonts):
    items, ctm, stack = [], [1, 0, 0, 1, 0, 0], []
    tm = [1, 0, 0, 1, 0, 0]
    tlm = list(tm)
    leading, font, size = 0.0, None, 12.0
    ops, i, n = [], 0, len(content) if content else 0
    while i < n:
        m = TOKEN.search(content, i)
        if not m:
            break
        i = m.end()
        if m.group(3) is not None:
            depth, j, buf = 1, m.start() + 1, bytearray()
            while j < n:
                ch = content[j]
                if ch == 0x5c:
                    buf += content[j:j + 2]; j += 2; continue
                if ch == 0x28:
                    depth += 1
                elif ch == 0x29:
                    depth -= 1
                    if depth == 0:
                        break
                buf.append(ch); j += 1
            ops.append(('str', _unescape(bytes(buf))))
            i = j + 1
            continue
        if m.group(2) is not None:
            hx = re.sub(rb'\s', b'', m.group(2))
            if len(hx) % 2:
                hx += b'0'
            try:
                ops.append(('str', bytes.fromhex(hx.decode())))
            except Exception:
                pass
            continue
        if m.group(1) is not None:
            ops.append(('name', m.group(1).decode('latin-1')))
            continue
        if m.group(4) is not None:
            ops.append(('num', float(m.group(4))))
            continue
        if m.group(5) is None:
            continue
        op = m.group(5)
        nums = [v for t, v in ops if t == 'num']
        names = [v for t, v in ops if t == 'name']
        try:
            if op == b'q':
                stack.append(list(ctm))
            elif op == b'Q':
                if stack:
                    ctm = stack.pop()
            elif op == b'cm' and len(nums) >= 6:
                ctm = _mul(nums[-6:], ctm)
            elif op == b'Tf':
                if names:
                    font = fonts.get(names[-1])
                if nums:
                    size = nums[-1]
            elif op == b'TL' and nums:
                leading = nums[-1]
            elif op in (b'Td', b'TD') and len(nums) >= 2:
                tx, ty = nums[-2], nums[-1]
                if op == b'TD':
                    leading = -ty
                tlm = [tlm[0], tlm[1], tlm[2], tlm[3],
                       tlm[4] + tx * tlm[0] + ty * tlm[2],
                       tlm[5] + tx * tlm[1] + ty * tlm[3]]
                tm = list(tlm)
            elif op == b'Tm' and len(nums) >= 6:
                tlm = list(nums[-6:]); tm = list(tlm)
            elif op == b'T*':
                tlm = [tlm[0], tlm[1], tlm[2], tlm[3], tlm[4], tlm[5] - leading]
                tm = list(tlm)
            elif op == b'BT':
                tm, tlm = [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 0, 0]
            elif op in (b'Tj', b"'", b'"'):
                if op in (b"'", b'"'):
                    tlm = [tlm[0], tlm[1], tlm[2], tlm[3], tlm[4], tlm[5] - leading]
                    tm = list(tlm)
                for t, v in reversed(ops):
                    if t == 'str':
                        txt, adv = _text(v, font)
                        trm = _mul(tm, ctm)
                        if txt.strip():
                            items.append((round(trm[5], 1), round(trm[4], 1),
                                          round(size * abs(trm[3] or 1), 1), txt, adv * size))
                        tm[4] += adv * size * tm[0]
                        break
            elif op == b'TJ':
                for t, v in ops:
                    if t == 'str':
                        txt, adv = _text(v, font)
                        trm = _mul(tm, ctm)
                        if txt.strip():
                            items.append((round(trm[5], 1), round(trm[4], 1),
                                          round(size * abs(trm[3] or 1), 1), txt, adv * size))
                        tm[4] += adv * size * tm[0]
                    elif t == 'num':
                        tm[4] += (-v / 1000.0) * size * tm[0]
        except Exception:
            pass
        ops = []
    return items


def page_item_lists(path):
    """按页返回 item 列表 —— 行聚类必须逐页做，否则不同页同 y 的行会被并成一行。"""
    doc = _Doc(path)
    out = []
    for pnum in doc.pages():
        pd = doc.objs[pnum][0]
        res = pd
        rn = doc.ref(pd, '/Resources')
        if rn and rn in doc.objs:
            res = doc.objs[rn][0]
        fonts = doc.fonts(res)
        m = re.search(rb'/Contents\s+(\d+)\s+\d+\s+R', pd)
        content = doc.stream(int(m.group(1))) if m else None
        items = _items(content, fonts)
        if items:
            out.append(items)
    return out


def page_items(path):
    out = []
    for items in page_item_lists(path):
        out.extend(items)
    return out


# ------------------------------------------------------------ 行列聚类
def rows_from_items(items, y_tol=3.0, gap_x=6.0):
    """按 y 聚行，行内按 x 间隔切单元格。"""
    items = sorted(items, key=lambda t: (-t[0], t[1]))
    lines = []
    for it in items:
        if lines and abs(lines[-1]['y'] - it[0]) <= y_tol:
            lines[-1]['items'].append(it)
        else:
            lines.append({'y': it[0], 'items': [it]})
    rows = []
    for ln in lines:
        cells, cur, prev_end = [], '', None
        for y, x, size, txt, w in sorted(ln['items'], key=lambda t: t[1]):
            if prev_end is not None and x - prev_end > gap_x:
                cells.append(cur.strip())
                cur = ''
            if cur and not cur.endswith(' ') and txt[:1].isascii() and cur[-1:].isascii():
                cur += ' '
            cur += txt
            prev_end = x + w
        cells.append(cur.strip())
        rows.append({'y': ln['y'], 'cells': cells})
    return rows


def load_blocks(path):
    """输出与 .doc 相同的 IR：('c', 单元格) 序列，按行拼接（保留空单元格）。"""
    blocks = []
    for items in page_item_lists(path):
        for r in rows_from_items(items):
            cells = [c for c in r['cells']]
            if not any(cells):
                continue
            # 单格且很长 -> 当段落
            if len(cells) == 1 and len(cells[0]) > 22:
                blocks.append(('p', cells[0]))
                continue
            for c in cells:
                blocks.append(('c', c))
    return blocks


if __name__ == '__main__':
    for i, items in enumerate(page_item_lists(sys.argv[1]), 1):
        for r in rows_from_items(items):
            print('[p%d] y=%7.1f :: %s' % (i, r['y'], ' | '.join(r['cells'])))
