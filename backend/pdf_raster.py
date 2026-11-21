#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小 PDF 矢量栅格化器（纯 numpy + Pillow）。
用途：对付"文字被转成曲线"的 PDF —— 这类文件没有字体对象、没有文本操作符，
任何文本解析器都读不出内容，只能先渲染成图再人工/OCR 识别。

只实现表格类 PDF 用得到的子集：q/Q、rg/RG、w、m/l/c/v/y/re/h、f/f*/S/s/B。
填充统一按奇偶规则（even-odd），与实际排版一致。
"""
import re
import sys
import zlib
from collections import defaultdict

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import pdf_adapter as pa  # noqa: E402

NUM = rb'[-+]?(?:\d+\.?\d*|\.\d+)'
TOK = re.compile(rb'(' + NUM + rb')|([A-Za-z\'"*]+)|(/[^\s/<>\[\]()]+)|(\((?:\\.|[^\\()])*\))|(<[0-9A-Fa-f\s]*>)')


def parse(content):
    """产出 (kind, payload) 事件：('fill', polys, color) / ('stroke', polylines, color, width)"""
    stack = []
    out = []
    ctm_stack = []
    ctm = (1, 0, 0, 1, 0, 0)
    color = (0, 0, 0)
    width = 1.0
    subpaths = []      # list of list[(x,y)]
    cur = []
    pos = (0.0, 0.0)
    start = (0.0, 0.0)

    def xf(p):
        a, b, c, d, e, f = ctm
        return (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)

    def flush(close=False):
        nonlocal cur
        if len(cur) >= 2:
            path = list(cur)
            if close:
                path.append(path[0])
            subpaths.append(path)
        elif len(cur) == 1:
            subpaths.append([cur[0], cur[0]])
        cur = []

    for m in TOK.finditer(content):
        if m.group(1) is not None:
            stack.append(float(m.group(1)))
            continue
        if m.group(3) is not None or m.group(4) is not None or m.group(5) is not None:
            stack.append(m.group(0))
            continue
        op = m.group(2)
        if op is None:
            continue
        s = op.decode('latin-1')
        if s == 'q':
            ctm_stack.append(ctm)
        elif s == 'Q':
            if ctm_stack:
                ctm = ctm_stack.pop()
        elif s == 'cm' and len(stack) >= 6:
            v = [x for x in stack[-6:]]
            a, b, c, d, e, f = v
            ca, cb, cc, cd, ce, cf = ctm
            ctm = (a * ca + b * cc, a * cb + b * cd,
                   c * ca + d * cc, c * cb + d * cd,
                   e * ca + f * cc + ce, e * cb + f * cd + cf)
        elif s in ('rg', 'RG') and len(stack) >= 3:
            color = tuple(min(1.0, max(0.0, x)) for x in stack[-3:])
        elif s == 'w' and stack:
            width = abs(float(stack[-1]))
        elif s == 'm' and len(stack) >= 2:
            flush()
            pos = (stack[-2], stack[-1])
            start = pos
            cur = [xf(pos)]
        elif s == 'l' and len(stack) >= 2:
            pos = (stack[-2], stack[-1])
            cur.append(xf(pos))
        elif s == 'c' and len(stack) >= 6:
            p1 = (stack[-6], stack[-5]); p2 = (stack[-4], stack[-3]); p3 = (stack[-2], stack[-1])
            x0, y0 = pos
            for i in range(1, 9):
                t = i / 8.0
                mt = 1 - t
                x = mt ** 3 * x0 + 3 * mt ** 2 * t * p1[0] + 3 * mt * t ** 2 * p2[0] + t ** 3 * p3[0]
                y = mt ** 3 * y0 + 3 * mt ** 2 * t * p1[1] + 3 * mt * t ** 2 * p2[1] + t ** 3 * p3[1]
                cur.append(xf((x, y)))
            pos = p3
        elif s in ('v', 'y') and len(stack) >= 4:
            cur.append(xf((stack[-2], stack[-1])))
            pos = (stack[-2], stack[-1])
        elif s == 're' and len(stack) >= 4:
            flush()
            x, y, w, h = stack[-4:]
            pts = [xf((x, y)), xf((x + w, y)), xf((x + w, y + h)), xf((x, y + h))]
            subpaths.append(pts + [pts[0]])
            pos = (x, y)
            start = pos
        elif s == 'h':
            if cur:
                cur.append(cur[0])
                pos = start
                flush()
        elif s in ('f', 'f*', 'F'):
            flush(close=True)
            if subpaths:
                out.append(('fill', list(subpaths), color))
            subpaths = []
        elif s in ('S', 's'):
            flush(close=(s == 's'))
            if subpaths:
                out.append(('stroke', list(subpaths), color, max(0.2, width)))
            subpaths = []
        elif s in ('B', 'B*', 'b', 'b*'):
            flush(close=s.startswith('b'))
            if subpaths:
                out.append(('fill', list(subpaths), color))
                out.append(('stroke', list(subpaths), color, max(0.2, width)))
            subpaths = []
        elif s == 'n':
            subpaths = []
        stack = []
    return out


def _fill_mask(shape, polys, scale, flip_height):
    """奇偶规则扫描线填充，返回该多边形的 mask（只覆盖 bbox 区域）。"""
    h, w = shape
    edges = []
    xs_all, ys_all = [], []
    for path in polys:
        for i in range(len(path) - 1):
            x0, y0 = path[i]
            x1, y1 = path[i + 1]
            if y0 == y1:
                continue
            edges.append((x0 * scale, y0 * scale, x1 * scale, y1 * scale))
            xs_all += [x0, x1]
            ys_all += [y0, y1]
    if not edges:
        return None
    x0 = max(0, int(min(xs_all) * scale) - 1)
    x1 = min(w - 1, int(max(xs_all) * scale) + 2)
    y0 = max(0, int(min(ys_all) * scale) - 1)
    y1 = min(h - 1, int(max(ys_all) * scale) + 2)
    if x1 <= x0 or y1 <= y0:
        return None
    E = np.array(edges, dtype=np.float64)
    ex0, ey0, ex1, ey1 = E[:, 0], E[:, 1], E[:, 2], E[:, 3]
    ymin = np.minimum(ey0, ey1)
    ymax = np.maximum(ey0, ey1)
    m = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=bool)
    for row in range(y0, y1 + 1):
        yc = row + 0.5
        sel = (ymin <= yc) & (ymax > yc)
        if not sel.any():
            continue
        t = (yc - ey0[sel]) / (ey1[sel] - ey0[sel])
        xc = ex0[sel] + t * (ex1[sel] - ex0[sel])
        xc.sort()
        for i in range(0, len(xc) - 1, 2):
            a = int(np.ceil(xc[i]))
            b = int(np.floor(xc[i + 1]))
            if b < a:
                continue
            m[row - y0, max(0, a - x0):min(m.shape[1], b - x0 + 1)] = True
    return (y0, x0, m)


def render(pdf_path, out_png, scale=3.0, dpi_max_px=4000, page_index=0):
    doc = pa._Doc(pdf_path)
    pages = doc.pages()
    if not pages:
        raise SystemExit('no page')
    pd = doc.objs[pages[min(page_index, len(pages) - 1)]][0]
    mbox = re.search(rb'/MediaBox\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', pd)
    if mbox:
        px0, py0, px1, py1 = [float(x) for x in mbox.groups()]
    else:
        px0, py0, px1, py1 = 0, 0, 595.276, 841.89
    W = int((px1 - px0) * scale)
    H = int((py1 - py0) * scale)
    if max(W, H) > dpi_max_px:
        f = dpi_max_px / max(W, H)
        scale *= f
        W, H = int(W * f), int(H * f)
    canvas = np.ones((H, W, 3), dtype=np.uint8) * 255

    rn = doc.ref(pd, '/Resources')
    res = doc.objs[rn][0] if rn and rn in doc.objs else pd
    m = re.search(rb'/Contents\s+(\d+)\s+\d+\s+R', pd)
    content = doc.stream(int(m.group(1))) if m else b''
    events = parse(content)

    def to_px(pt):
        return (pt[0] - px0) * scale, (py1 - pt[1]) * scale

    for ev in events:
        if ev[0] == 'fill':
            polys = [[to_px(p) for p in path] for path in ev[1]]
            got = _fill_mask((H, W), polys, 1.0, H)
            if got is None:
                continue
            y0, x0, mask = got
            col = tuple(int(c * 255) for c in ev[2])
            region = canvas[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]]
            region[mask] = col
        else:
            _, paths, col, width = ev
            img = Image.fromarray(canvas)
            from PIL import ImageDraw
            dr = ImageDraw.Draw(img)
            c = tuple(int(x * 255) for x in col)
            for path in paths:
                pts = [to_px(p) for p in path]
                if len(pts) >= 2:
                    dr.line(pts, fill=c, width=max(1, int(width * scale)))
            canvas = np.array(img)
    Image.fromarray(canvas).save(out_png)
    return out_png, W, H, len(events)


if __name__ == '__main__':
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    if len(sys.argv) > 4:
        print(render(sys.argv[1], sys.argv[2], scale, page_index=int(sys.argv[4])))
    else:
        print(render(sys.argv[1], sys.argv[2], scale))
