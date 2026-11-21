# 后端说明（BE-01 / BE-02）

对应 `PROJECT_HANDOFF.md`：§8.1 路由、§8.2 错误结构、§8.3 培养方案上传、§8.4 成长路线、§8.5 机会与资源。

## 1. 现在能跑什么

打开 <http://127.0.0.1:8000/> 会看到一张接口清单（HTML 首页），点路径即可试。
`/favicon.ico` 返回 204，不会再往日志里刷 404。

| 能力 | 状态 |
|---|---|
| `GET /` 接口清单首页 | 已实现 |
| `GET /healthz` | 已实现 |
| `POST /api/v1/training-plans`（Word / PDF / 图片） | 已实现，含完整度报警 |
| `GET /api/v1/training-plans/{plan_id}` | 已实现（结果落盘，重启可读） |
| `POST /api/v1/growth-plans` | demo 模式已实现；`mode=ai` 返回 503 待接入 |
| `GET /api/v1/opportunities`、`/{id}` | 已实现（fixture，`source: demo`） |
| `GET /api/v1/resources`、`/{id}` | 已实现（fixture，`source: demo`） |

未知路径返回 404 + `NOT_FOUND`，并提示去根路径看清单。

解析链路（`ingest.py` → `curriculum_parser.py`）**零第三方依赖**；`api/` 只是 HTTP 翻译层。

## 2. 启动

### 方式 A：零依赖开发服务器（当前环境可直接跑）

```bash
cd backend
python api/devserver.py --port 8000
# → http://127.0.0.1:8000   （打开根路径就是接口清单）
```

Windows 可直接双击 `backend/start_api.bat`，或 `start_api.bat 8010` 换端口。
**注意**：devserver 没有热重载，改完代码要 Ctrl+C 重启（FastAPI 版用 `--reload` 可自动重载）。

### 方式 B：FastAPI（装上依赖即用，路由与 A 完全一致）

```bash
cd backend
pip install -r requirements.txt
uvicorn api.app_fastapi:app --reload --port 8000
```

两者的业务逻辑都在 `api/handlers.py`，切换不影响前端。

## 3. 前端对接

Vite 侧新增环境变量：

```bash
# .env.local
VITE_API_BASE_URL=http://127.0.0.1:8000
```

CORS 已允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`（见 `devserver.ALLOW_ORIGINS` / FastAPI `add_middleware`）。换端口时同步改这两处。

上传示例（单文件 / 多文件同一写法）：

```js
const fd = new FormData()
fd.append('file', file)                 // 多文件就再 append 几次
const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/training-plans`, {
  method: 'POST', body: fd,
})
```

## 4. 接口与样例

### POST /api/v1/training-plans

`multipart/form-data`，字段 `file`（必填，**可重复**）、`mode`（`parsed`/`demo`，可选）。

- 一个 `file` → 一份方案
- 多个 `file` → **合并成一份方案**（同一份材料被拆成多个文件时用这个）。按（课程名, 学分, 课程组）去重，`source.files` 列出每个来源文件
- 200：`parse_status: complete | partial`，响应体见 `CONTRACT_EXT.md` 第 2 节
- 400 `EMPTY_FILE` / 413 `FILE_TOO_LARGE` / 415 `UNSUPPORTED_FILE_TYPE` / 422 `MISSING_FILE`
- **422 `PARSING_FAILED`**：一份课程都没解析出来，`details[0]` 带 `alerts` 与 `recommended_upload`

失败样例（无文字层 PDF）：

```json
{
  "error": {
    "code": "PARSING_FAILED",
    "message": "这份文件没有解析出任何课程。",
    "request_id": "req_5f3c1a9d2b7e",
    "details": [{
      "alerts": [{"code": "NO_TEXT_LAYER", "severity": "high",
                  "message": "这份文件没有文字层（PDF 文字已转曲），无法直接读取内容。",
                  "user_action": "请优先上传 Word 原件（.docx）；若只能给 PDF，请在 Word/Excel 里用「另存为 PDF」，不要扫描或截图。"}],
      "recommended_upload": {"format": "docx", "label": "Word 原件（.docx）"}
    }]
  }
}
```

### POST /api/v1/growth-plans

```json
{ "plan_id": "plan_20261121_ab12cd", "interests": ["数据分析"], "mode": "demo",
  "completed_course_ids": ["C001"] }
```

返回 8 个学期节点，`source: "demo"`。

- **规则生成**（`api/growth.py`）：每学期目标 = 该学期课程 + 该组的学分缺口 + 兴趣实践。
  缺口 = 组要求学分 − 方案内已排课程学分；只把最大的 6 条做成目标并摊到 3–7 学期，
  其余放在 `summary.groups_with_gap`，避免八个学期都刷同一句话。
- **结构校验**：返回前必须过 `growth.validate()`（学期 1–8 有序、goal id 唯一、
  `course_ids` 都能在方案里找到、标题 ≤60 字、actions ≤5 条）。校验不过返回 `502 GROWTH_INVALID`，不给前端坏数据。
- `completed_course_ids` 是可选扩展字段，用于在 `summary.completed_credits` 里标注已修学分。
- `mode: "ai"` → `503 AI_NOT_CONFIGURED`（AI 适配层未接）。

### GET /api/v1/opportunities | /resources

支持 `category`（机会另有 `status`）过滤，返回 `{ "items": [...], "total": n }`。
当前全部为 `source: "demo"` 的固定数据，字段按 §8.5 定义，`official_url` 留空等资料同学补。

## 5. 存储与生命周期

| 路径 | 内容 | 说明 |
|---|---|---|
| `var/plans/<plan_id>.json` | 解析结果 | 重启仍可读；后续换数据库时替换这一层 |
| `var/uploads/` | 上传临时文件 | 解析完成后立刻删除 |

单进程、无鉴权、无分页。`429` 限流与多实例部署未做，属于上线前的事。

## 6. 验证

```bash
python api/smoke_test.py http://127.0.0.1:8000
```

当前结果：**16/16 通过**，覆盖正常上传、读回、成长路线、机会/资源、404、空请求 422、无文字层 422。

格式矩阵另见 `python verify_formats.py`（六种输入 × 完整度/HTTP 状态）。

## 7. 已知限制

- 同一份文件重复上传会产生不同 `plan_id`，暂不去重。
- `mode=ai` 未接；接法见 `CONTRACT_EXT.md` 第 6 节（AI 适配层接收结构化输入、校验结构化输出）。
- 无文件保留期策略（§8.1 要求公开部署前定）。
- 图片输入必须带识别结果（`--ocr-cache`），服务端尚未内置视觉模型，接法见 `CONTRACT_EXT.md` 第 6 节。
