#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
业务层：与框架无关。每个函数返回 (status_code, body_dict)。
FastAPI / 标准库 devserver 都只做 HTTP 翻译，不写业务。

对应 PROJECT_HANDOFF.md：
  §8.1 路由  §8.2 错误信封  §8.3 培养方案上传  §8.4 成长路线  §8.5 机会与资源
"""
import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ingest  # noqa: E402
import to_api_v1  # noqa: E402
import growth  # noqa: E402

MAX_FILE_BYTES = 20 * 1024 * 1024       # §8.3 上限待定，先给 20MB
ALLOWED_EXT = {'.docx', '.doc', '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}

OPPORTUNITIES = []   # 由 fixtures 注入
RESOURCES = []


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []

    def body(self, request_id):
        return {'error': {'code': self.code, 'message': self.message,
                          'request_id': request_id, 'details': self.details}}


def new_request_id():
    return 'req_' + uuid.uuid4().hex[:12]


def new_plan_id():
    return 'plan_' + time.strftime('%Y%m%d') + '_' + uuid.uuid4().hex[:6]


# ------------------------------------------------------------------ 存储
PLAN_DIR = os.path.join(ROOT, 'var', 'plans')
UPLOAD_DIR = os.path.join(ROOT, 'var', 'uploads')


def _ensure_dirs():
    os.makedirs(PLAN_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_plan(api):
    _ensure_dirs()
    with open(os.path.join(PLAN_DIR, api['plan_id'] + '.json'), 'w', encoding='utf-8') as f:
        json.dump(api, f, ensure_ascii=False)


def load_plan(plan_id):
    if not plan_id or '/' in plan_id or '\\' in plan_id or '..' in plan_id:
        return None
    path = os.path.join(PLAN_DIR, plan_id + '.json')
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return None


# ------------------------------------------------------------------ /healthz
def healthz():
    return 200, {'status': 'ok', 'version': '0.1.0', 'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


# ------------------------------------------------------------------ 上传解析
def create_training_plan(file_name, content, mode='parsed'):
    """单文件入口（保持向后兼容）"""
    return create_training_plan_multi([(file_name, content)], mode)


def create_training_plan_multi(items, mode='parsed'):
    """items: [(filename, bytes)]。多个文件 = 同一份方案被拆开，合并成一个 plan。"""
    if not items:
        raise ApiError(400, 'EMPTY_FILE', '文件为空，请重新选择。')
    for name, content in items:
        if not content:
            raise ApiError(400, 'EMPTY_FILE', '%s 是空文件。' % (name or '(未命名)'))
        if len(content) > MAX_FILE_BYTES:
            raise ApiError(413, 'FILE_TOO_LARGE',
                           '%s 超过 %d MB 上限。' % (name, MAX_FILE_BYTES // 1024 // 1024))
        ext = os.path.splitext(name or '')[1].lower()
        if ext not in ALLOWED_EXT:
            raise ApiError(415, 'UNSUPPORTED_FILE_TYPE',
                           '%s：当前支持 Word（.docx/.doc）、PDF 与图片。' % (name or ''),
                           details=[{'file': name, 'ext': ext or None,
                                     'allowed': sorted(ALLOWED_EXT)}])

    _ensure_dirs()
    paths = []
    try:
        for name, content in items:
            safe = os.path.basename(name).replace(' ', '_')
            tmp = os.path.join(UPLOAD_DIR, uuid.uuid4().hex[:8] + '_' + safe)
            with open(tmp, 'wb') as f:
                f.write(content)
            paths.append(tmp)
        try:
            api, cur, comp, fmt = ingest.ingest_many(
                paths, None, new_plan_id(),
                'demo' if mode == 'demo' else 'parsed',
                names=[n for n, _ in items])
        except SystemExit as e:
            raise ApiError(415, 'UNSUPPORTED_FILE_TYPE', str(e))
        except Exception as e:
            raise ApiError(500, 'PARSING_ERROR', '解析过程出错，请重试或换用 Word 原件。',
                           details=[{'hint': type(e).__name__}])
    finally:
        for p in paths:
            try:
                os.remove(p)
            except OSError:
                pass

    status = to_api_v1.http_status(api)
    if status == 422:
        raise ApiError(422, 'PARSING_FAILED',
                       '这份文件没有解析出任何课程。' if len(items) == 1
                       else '这些文件合起来没有解析出任何课程。',
                       details=[{'alerts': comp['alerts'],
                                 'recommended_upload': comp['recommended_upload']}])
    save_plan(api)
    return 200, api


def get_training_plan(plan_id):
    api = load_plan(plan_id)
    if not api:
        raise ApiError(404, 'PLAN_NOT_FOUND', '找不到该培养方案，请重新上传。')
    return 200, api


# ------------------------------------------------------------------ 成长路线
def create_growth_plan(plan_id, interests=None, mode='demo', completed_ids=None):
    if mode not in ('demo', 'ai'):
        raise ApiError(422, 'INVALID_MODE', 'mode 只允许 demo 或 ai。')
    plan = load_plan(plan_id) if plan_id else None
    if plan_id and not plan:
        raise ApiError(404, 'PLAN_NOT_FOUND', '找不到对应培养方案，请重新上传。')

    if mode == 'ai':
        raise ApiError(503, 'AI_NOT_CONFIGURED',
                       'AI 服务尚未配置，可先用演示模式（mode=demo）。')

    base = plan or {'plan_id': None, 'courses': [], 'groups': []}
    out = growth.build(base, interests, completed_ids, mode)
    problems = growth.validate(out, plan)
    if problems:
        raise ApiError(502, 'GROWTH_INVALID',
                       '生成结果未通过结构校验，已拒绝返回。',
                       details=[{'problems': problems[:5]}])
    return 200, out


# ------------------------------------------------------------------ 机会 / 资源
def list_opportunities(category=None, status=None):
    items = [o for o in OPPORTUNITIES
             if (not category or o['category'] == category)
             and (not status or o['status'] == status)]
    return 200, {'items': items, 'total': len(items)}


def get_opportunity(oid):
    for o in OPPORTUNITIES:
        if o['id'] == oid:
            return 200, o
    raise ApiError(404, 'OPPORTUNITY_NOT_FOUND', '找不到该机会记录。')


def list_resources(category=None):
    items = [r for r in RESOURCES if not category or r['category'] == category]
    return 200, {'items': items, 'total': len(items)}


def get_resource(rid):
    for r in RESOURCES:
        if r['id'] == rid:
            return 200, r
    raise ApiError(404, 'RESOURCE_NOT_FOUND', '找不到该资源记录。')


def bind_fixtures(opps, res):
    global OPPORTUNITIES, RESOURCES
    OPPORTUNITIES = opps
    RESOURCES = res
