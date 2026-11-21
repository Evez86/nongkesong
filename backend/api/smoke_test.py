#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
接口冒烟测试（QA-01 用）。对运行中的服务发真实 HTTP 请求，跑完 §8.1 的全部路由。
用法：python api/smoke_test.py [http://127.0.0.1:8010]
"""
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8010'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def req(method, path, body=None, headers=None):
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8') or '{}')


def multipart(path, field='file', filename=None):
    filename = filename or os.path.basename(path)
    ctype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    boundary = '----pineletters' + str(abs(hash(filename)) % 100000)
    with open(path, 'rb') as f:
        content = f.read()
    body = b''.join([
        ('--%s\r\n' % boundary).encode(),
        ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field, filename)).encode('utf-8'),
        ('Content-Type: %s\r\n\r\n' % ctype).encode(),
        content, b'\r\n',
        ('--%s--\r\n' % boundary).encode(),
    ])
    return body, {'Content-Type': 'multipart/form-data; boundary=%s' % boundary}


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('%s %-38s %s' % ('PASS' if ok else 'FAIL', name, detail))


def main():
    s, b = req('GET', '/healthz')
    check('GET /healthz', s == 200 and b.get('status') == 'ok', '%s' % s)

    # 1) 正常上传（Word 原件）
    doc = r'C:\Users\JUSTI\Documents\xwechat_files\wxid_lq0el398u5th22_1d3f\msg\file\2026-11\8-工学院理科试验班（智能装备）本科人才培养方案.doc'
    plan_id = None
    if os.path.exists(doc):
        body, hdrs = multipart(doc)
        s, b = req('POST', '/api/v1/training-plans', body, hdrs)
        plan_id = b.get('plan_id')
        check('POST /training-plans (Word)', s == 200 and b.get('parse_status') == 'complete',
              'courses=%d status=%s http=%s' % (len(b.get('courses', [])), b.get('parse_status'), s))
        check('  响应含契约扩展字段',
              all(k in b.get('courses', [{}])[0] for k in ('terms', 'group', 'track'))
              and 'groups' in b and 'completeness' in b)
        check('  completeness.level=full', (b.get('completeness') or {}).get('level') == 'full',
              str((b.get('completeness') or {}).get('score')))

    # 2) 读回
    if plan_id:
        s, b = req('GET', '/api/v1/training-plans/' + plan_id)
        check('GET /training-plans/{id}', s == 200 and b.get('plan_id') == plan_id, '%s' % s)
    s, b = req('GET', '/api/v1/training-plans/plan_nope')
    check('GET 不存在的 plan → 404', s == 404 and b['error']['code'] == 'PLAN_NOT_FOUND')

    # 3) 成长路线（demo）
    s, b = req('POST', '/api/v1/growth-plans',
               json.dumps({'plan_id': plan_id, 'interests': ['数据分析'], 'mode': 'demo'}).encode(),
               {'Content-Type': 'application/json'})
    terms = b.get('terms') or []
    check('POST /growth-plans (demo)', s == 200 and len(terms) == 8 and b.get('source') == 'demo',
          'terms=%d' % len(terms))
    if s == 200:
        ids = [t['term'] for t in terms]
        check('  学期 1..8 有序', ids == list(range(1, 9)), str(ids))
        goal_ids = [g['id'] for t in terms for g in t.get('goals', [])]
        check('  goal id 唯一', len(goal_ids) == len(set(goal_ids)), '%d 个目标' % len(goal_ids))
        known = {c['id'] for c in b.get('courses', [])} | {
            c['id'] for c in (req('GET', '/api/v1/training-plans/' + plan_id)[1].get('courses') or [])}
        bad = [cid for t in terms for g in t.get('goals', []) for cid in g.get('course_ids', [])
               if cid not in known]
        check('  course_ids 都可解析', not bad, str(bad[:3]))
        gap = [g for t in terms for g in t.get('goals', []) if '还差' in (g.get('title') or '')]
        check('  含缺口驱动目标', bool(gap), '%d 条' % len(gap))
    s, b = req('POST', '/api/v1/growth-plans', json.dumps({'mode': 'ai'}).encode(),
               {'Content-Type': 'application/json'})
    check('POST /growth-plans (mode=ai) → 503', s == 503 and b['error']['code'] == 'AI_NOT_CONFIGURED')
    s, b = req('POST', '/api/v1/growth-plans', json.dumps({'mode': 'nope'}).encode(),
               {'Content-Type': 'application/json'})
    check('POST /growth-plans (非法 mode) → 422', s == 422 and b['error']['code'] == 'INVALID_MODE')
    s, b = req('POST', '/api/v1/growth-plans',
               json.dumps({'plan_id': 'plan_nope', 'mode': 'demo'}).encode(),
               {'Content-Type': 'application/json'})
    check('POST /growth-plans (未知 plan) → 404', s == 404)

    # 4) 机会 / 资源
    s, b = req('GET', '/api/v1/opportunities')
    check('GET /opportunities', s == 200 and b['total'] >= 1, 'total=%s' % b.get('total'))
    s, b = req('GET', '/api/v1/opportunities?category=research')
    check('GET /opportunities?category=research', s == 200 and all(
        o['category'] == 'research' for o in b['items']), 'total=%s' % b.get('total'))
    s, b = req('GET', '/api/v1/opportunities/opp_demo_001')
    check('GET /opportunities/{id}', s == 200 and b['id'] == 'opp_demo_001')
    s, b = req('GET', '/api/v1/opportunities/opp_nope')
    check('GET 不存在的机会 → 404', s == 404)
    s, b = req('GET', '/api/v1/resources')
    check('GET /resources', s == 200 and b['total'] >= 1)
    s, b = req('GET', '/api/v1/resources/res_demo_001')
    check('GET /resources/{id}', s == 200 and b['id'] == 'res_demo_001')

    # 5) 错误路径
    body = b''
    s, b = req('POST', '/api/v1/training-plans', body, {'Content-Type': 'multipart/form-data; boundary=x'})
    check('空请求 → 422', s == 422, b.get('error', {}).get('code'))

    # 6) 无文字层 PDF（无 OCR）→ 422 PARSING_FAILED
    pdf = r'C:\Users\JUSTI\Desktop\另一学院培养方案\A专业必修.pdf'
    if os.path.exists(pdf):
        body, hdrs = multipart(pdf)
        s, b = req('POST', '/api/v1/training-plans', body, hdrs)
        check('无文字层 PDF → 422', s == 422 and b['error']['code'] == 'PARSING_FAILED',
              (b['error']['details'][0]['recommended_upload']['label']
               if b['error'].get('details') else ''))

    bad = [r for r in results if not r[1]]
    print('\n%d/%d passed' % (len(results) - len(bad), len(results)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
