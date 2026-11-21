#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
零依赖开发服务器（标准库 http.server）。路由与 FastAPI 版完全一致，
用于"环境里没有 fastapi / 不能联网"的机器上跑通前端联调。

启动：python api/devserver.py [--port 8000]
"""
import argparse
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fixtures  # noqa: E402
import handlers  # noqa: E402

handlers.bind_fixtures(fixtures.OPPORTUNITIES, fixtures.RESOURCES)

ALLOW_ORIGINS = {'http://localhost:5173', 'http://127.0.0.1:5173'}

ENDPOINTS = [
    ('GET', '/healthz', '服务可用性', '/healthz'),
    ('GET', '/api/v1/opportunities', '机会列表，可选 ?category= &status=', '/api/v1/opportunities'),
    ('GET', '/api/v1/opportunities/{id}', '机会详情', '/api/v1/opportunities/opp_demo_001'),
    ('GET', '/api/v1/resources', '资源列表，可选 ?category=', '/api/v1/resources'),
    ('GET', '/api/v1/resources/{id}', '资源详情', '/api/v1/resources/res_demo_001'),
    ('POST', '/api/v1/training-plans', '上传培养方案（multipart，字段 file）', None),
    ('GET', '/api/v1/training-plans/{plan_id}', '读回上次解析结果（id 由上传返回）', None),
    ('POST', '/api/v1/growth-plans', '生成八学期成长路线（mode=demo|ai）', None),
]

INDEX_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>松果来信 API</title>
<style>
 body{font:15px/1.6 -apple-system,"Segoe UI",system-ui,sans-serif;margin:0;
      padding:40px 28px;background:#f6f1e7;color:#3b2a1d}
 .card{max-width:860px;margin:0 auto;background:#fffdf8;border:1px solid #e6d9c2;
       border-radius:14px;padding:28px 30px;box-shadow:0 6px 18px rgba(80,50,20,.07)}
 h1{margin:0 0 4px;font-size:22px}
 .sub{color:#8a7457;margin-bottom:22px;font-size:13px}
 table{border-collapse:collapse;width:100%;font-size:14px}
 td{padding:8px;border-bottom:1px dashed #eee3d0;vertical-align:top}
 td.m{font-weight:600;white-space:nowrap;width:52px}
 .get{color:#2f6b3a}.post{color:#8a5a2b}
 td.p{font-family:Consolas,monospace;white-space:nowrap}
 td.p a{color:#2f5d8a;text-decoration:none}
 td.p a:hover{text-decoration:underline}
 .no{color:#a89880;font-size:13px}
 .tip{margin-top:20px;padding:12px 14px;background:#fdf6e6;border-left:3px solid #d9a441;
      border-radius:6px;font-size:13px;color:#6b5537}
 code{background:#f1e8d6;padding:1px 5px;border-radius:4px;font-size:13px}
 .cmd{margin-top:8px;background:#2b2118;color:#e8dcc6;padding:10px 12px;border-radius:8px;
      font-family:Consolas,monospace;font-size:12.5px;overflow-x:auto}
</style></head><body><div class="card">
<h1>松果来信 API</h1>
<div class="sub">v0.1.0 · 本地开发服务 · 列表统一返回 { items, total }</div>
<table>%ROWS%</table>
<div class="tip">
只有 <b>GET</b> 接口可以点开看结果；<b>POST</b> 接口需要前端或命令行发请求（浏览器地址栏只能发 GET，所以点了会 404）。
<br><b>想用浏览器试上传？</b>打开 <a href="/ui"><code>/ui</code></a> —— 内部核对页，能上传文件并把结果渲染成表格。
<div class="cmd">curl.exe -X POST http://127.0.0.1:%PORT%/api/v1/training-plans -F "file=@D:\\路径\\培养方案.docx"</div>
</div>
</div></body></html>"""

def _rows_html(port):
    out = []
    for method, path, desc, sample in ENDPOINTS:
        cls = 'get' if method == 'GET' else 'post'
        if sample:
            cell = '<a href="%s">%s</a>' % (sample, path)
        else:
            cell = '%s <span class="no">— 需 POST，地址栏打不开</span>' % path
        out.append('<tr><td class="m %s">%s</td><td class="p">%s</td><td>%s</td></tr>'
                   % (cls, method, cell, desc))
    return '\n'.join(out)


def index_html(port):
    return (INDEX_HTML.replace('%ROWS%', _rows_html(port))
            .replace('%PORT%', str(port)))


def parse_multipart(body, ctype):
    m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', ctype or '')
    if not m:
        return {}, {}
    boundary = (m.group(1) or m.group(2)).strip().encode()
    fields, files = {}, {}
    for part in body.split(b'--' + boundary):
        if not part or part.strip() in (b'--', b''):
            continue
        if part.startswith(b'\r\n'):
            part = part[2:]
        head, _, data = part.partition(b'\r\n\r\n')
        if data.endswith(b'\r\n'):
            data = data[:-2]
        head_s = head.decode('utf-8', 'replace')
        mn = re.search(r'name="([^"]*)"', head_s)
        if not mn:
            continue
        mf = re.search(r'filename="([^"]*)"', head_s)
        if mf:
            files.setdefault(mn.group(1), []).append((mf.group(1), data))
        else:
            fields[mn.group(1)] = data.decode('utf-8', 'replace')
    return fields, files


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write('[api] ' + fmt % args + '\n')

    # ---------------- 基础 ----------------
    def _cors(self):
        origin = self.headers.get('Origin')
        if origin in ALLOW_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, status, payload, request_id=None):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        if request_id:
            self.send_header('X-Request-Id', request_id)
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status, html):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n) if n else b''

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    # ---------------- 路由 ----------------
    def do_GET(self):
        rid = handlers.new_request_id()
        u = urlparse(self.path)
        p, q = u.path.rstrip('/'), parse_qs(u.query)
        try:
            if p in ('', '/'):
                return self._html(200, index_html(getattr(self.server, 'server_port', 8000)))
            if p == '/ui':
                path = os.path.join(HERE, 'ui.html')
                if os.path.exists(path):
                    return self._html(200, open(path, encoding='utf-8').read())
                return self._html(404, '<p>ui.html 缺失</p>')
            if p == '/favicon.ico':
                self.send_response(204)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if p == '/api/v1':
                return self._json(200, {'name': '松果来信 API', 'version': '0.1.0',
                                        'endpoints': [e[0] + ' ' + e[1] for e in ENDPOINTS]}, rid)
            if p == '/healthz':
                return self._dispatch(handlers.healthz(), rid)
            if p == '/api/v1/opportunities':
                return self._dispatch(handlers.list_opportunities(
                    (q.get('category') or [None])[0], (q.get('status') or [None])[0]), rid)
            m = re.fullmatch(r'/api/v1/opportunities/([^/]+)', p)
            if m:
                return self._dispatch(handlers.get_opportunity(m.group(1)), rid)
            if p == '/api/v1/resources':
                return self._dispatch(handlers.list_resources((q.get('category') or [None])[0]), rid)
            m = re.fullmatch(r'/api/v1/resources/([^/]+)', p)
            if m:
                return self._dispatch(handlers.get_resource(m.group(1)), rid)
            m = re.fullmatch(r'/api/v1/training-plans/([^/]+)', p)
            if m:
                return self._dispatch(handlers.get_training_plan(m.group(1)), rid)
            raise handlers.ApiError(404, 'NOT_FOUND', '没有这个接口。可用接口见根路径 / 。')
        except handlers.ApiError as e:
            return self._json(e.status, e.body(rid), rid)

    def do_POST(self):
        rid = handlers.new_request_id()
        u = urlparse(self.path)
        p = u.path.rstrip('/')
        try:
            if p == '/api/v1/training-plans':
                ctype = self.headers.get('Content-Type', '')
                fields, files = parse_multipart(self._body(), ctype)
                items = files.get('file') or files.get('files') or []
                if not items:
                    raise handlers.ApiError(422, 'MISSING_FILE', '请用表单字段 file 上传文件。')
                return self._dispatch(handlers.create_training_plan_multi(
                    items, fields.get('mode', 'parsed')), rid)
            if p == '/api/v1/growth-plans':
                try:
                    payload = json.loads(self._body() or b'{}')
                except json.JSONDecodeError:
                    raise handlers.ApiError(422, 'INVALID_JSON', '请求体不是合法 JSON。')
                return self._dispatch(handlers.create_growth_plan(
                    payload.get('plan_id'), payload.get('interests'),
                    payload.get('mode') or 'demo',
                    payload.get('completed_course_ids')), rid)
            raise handlers.ApiError(404, 'NOT_FOUND', '没有这个接口。')
        except handlers.ApiError as e:
            return self._json(e.status, e.body(rid), rid)

    def _dispatch(self, result, rid):
        status, payload = result
        self._json(status, payload, rid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8000')))
    ap.add_argument('--host', default='127.0.0.1')
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print('松果来信 API（devserver） listening on http://%s:%d' % (a.host, a.port), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止（Ctrl+C）。', flush=True)
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
