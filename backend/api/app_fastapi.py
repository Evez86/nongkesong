#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI 版入口（按 PROJECT_HANDOFF.md §4.1 的技术方向）。
依赖：pip install -r requirements.txt

启动：uvicorn api.app_fastapi:app --reload --port 8000
本机没有 fastapi 时，用 api/devserver.py，路由与响应完全一致。
"""
import json
import os
import sys

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import fixtures  # noqa: E402
import handlers  # noqa: E402

handlers.bind_fixtures(fixtures.OPPORTUNITIES, fixtures.RESOURCES)

app = FastAPI(title='松果来信 API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type'],
)


@app.exception_handler(handlers.ApiError)
async def api_error_handler(request: Request, exc: handlers.ApiError):
    rid = handlers.new_request_id()
    return JSONResponse(status_code=exc.status, content=exc.body(rid),
                        headers={'X-Request-Id': rid})


@app.get('/')
def index():
    import devserver
    return HTMLResponse(devserver.index_html(8000))


@app.get('/ui')
def ui():
    import devserver
    path = os.path.join(devserver.HERE, 'ui.html')
    return HTMLResponse(open(path, encoding='utf-8').read())


@app.get('/favicon.ico')
def favicon():
    return Response(status_code=204)


@app.get('/api/v1')
def api_index():
    return {'name': '松果来信 API', 'version': '0.1.0',
            'endpoints': [m + ' ' + p for m, p, _ in __import__('devserver').ENDPOINTS]}


@app.get('/healthz')
def healthz():
    return handlers.healthz()[1]


@app.post('/api/v1/training-plans')
async def create_training_plan(files: list[UploadFile] = File(...), mode: str = Form('parsed')):
    items = [(f.filename, await f.read()) for f in files]
    return handlers.create_training_plan_multi(items, mode)[1]


@app.get('/api/v1/training-plans/{plan_id}')
def get_training_plan(plan_id: str):
    return handlers.get_training_plan(plan_id)[1]


@app.post('/api/v1/growth-plans')
async def create_growth_plan(request: Request):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise handlers.ApiError(422, 'INVALID_JSON', '请求体不是合法 JSON。')
    return handlers.create_growth_plan(payload.get('plan_id'), payload.get('interests'),
                                       payload.get('mode') or 'demo',
                                       payload.get('completed_course_ids'))[1]


@app.get('/api/v1/opportunities')
def list_opportunities(category: str | None = None, status: str | None = None):
    return handlers.list_opportunities(category, status)[1]


@app.get('/api/v1/opportunities/{oid}')
def get_opportunity(oid: str):
    return handlers.get_opportunity(oid)[1]


@app.get('/api/v1/resources')
def list_resources(category: str | None = None):
    return handlers.list_resources(category)[1]


@app.get('/api/v1/resources/{rid}')
def get_resource(rid: str):
    return handlers.get_resource(rid)[1]


@app.api_route('/{path:path}', methods=['GET', 'POST'])
def fallback(path: str, request: Request):
    rid = handlers.new_request_id()
    return JSONResponse(status_code=404,
                        content={'error': {'code': 'NOT_FOUND',
                                           'message': '没有这个接口。可用接口见根路径 / 。',
                                           'request_id': rid, 'details': []}},
                        headers={'X-Request-Id': rid})
