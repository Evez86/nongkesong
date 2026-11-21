# 松果来信 · 后端

把学校给的**培养方案**（Word / PDF / 图片）解析成前端能直接渲染的结构化课程数据，并据此生成四年成长路线。

对应 `PROJECT_HANDOFF.md` 的 BE-01 / BE-02 / BE-03 与 BE-04 的接口部分。
前端是独立的 React 应用（Vite，默认 5173），通过 `/api/v1` 取数据。

---

## 状态

| 任务 | 内容 | 状态 |
|---|---|---|
| BE-01 | FastAPI 骨架、健康检查、统一错误结构 | ✅（另附零依赖 devserver） |
| BE-02 | 培养方案解析：Word / PDF / 图片，多文件合并 | ✅ 两份真实样本验证 |
| BE-03 | 成长路线（规则驱动 + 结构校验；AI 分支预留） | ✅ |
| BE-04 | 机会 / 资源读取接口 | ✅ 接口就绪，数据待资料同学替换 |

---

## 快速开始

```bash
cd backend

# A. 零依赖，立刻能跑（推荐先用这个）
python api/devserver.py --port 8000
#   Windows 也可以直接双击 start_api.bat

# B. FastAPI（装依赖后，路由与 A 完全一致）
pip install -r requirements.txt
uvicorn api.app_fastapi:app --reload --port 8000
```

- <http://127.0.0.1:8000/> — 接口清单
- <http://127.0.0.1:8000/ui> — 内部核对页（拖文件上传，看解析结果）

命令行跑完整条链路（不需要起服务）：

```bash
python pipeline.py "培养方案.docx"
# → out/api/plan.json        接口响应体
# → out/pipeline_report.md   人看的报告
```

---

## 支持的文件（按识别效果排序）

| 优先级 | 格式 | 说明 |
|---|---|---|
| 1 | **`.docx`（Word 原件）** | 文字层 + 真实表格，字段最全 |
| 2 | `.doc` | 解析效果相同，建议另存为 `.docx` |
| 3 | 含文字层的 PDF | 表格靠坐标还原，合并单元格/跨页可能丢行 |
| 4 | 转曲 / 扫描 PDF | 无文字层，须先转图识别 |
| 5 | 图片 | 无版面结构，不建议 |

> 实测：某学院给的 8 份 PDF **全部没有文字层**（0 个字体对象、0 个文本操作符），任何文本库都读不出内容。所以上传入口必做文字层探测，无文字层时走识别分支并给出「请传 Word 原件」的明确提示，而不是静默失败。

---

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` `/ui` `/healthz` | 清单页 / 核对页 / 可用性 |
| POST | `/api/v1/training-plans` | 上传解析，`file` 可重复（多文件合并成一份） |
| GET | `/api/v1/training-plans/{plan_id}` | 读回上次结果 |
| POST | `/api/v1/growth-plans` | 八学期路线（`mode=demo\|ai`） |
| GET | `/api/v1/opportunities` `/{id}` | 机会（当前 fixture） |
| GET | `/api/v1/resources` `/{id}` | 资源（当前 fixture） |

错误统一信封：`{"error": {"code", "message", "request_id", "details"}}`。
状态码与错误码清单见 [docs/BACKEND.md](docs/BACKEND.md)。

---

## 测试

```bash
python api/smoke_test.py http://127.0.0.1:8000   # 22 项接口测试
python verify_formats.py                          # 6 种输入的格式矩阵
```

当前 **22/22 通过**。

---

## 文档

| 文件 | 内容 |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | **技术文档主入口**：架构、数据流、数据模型、关键设计决策、术语表、新人阅读顺序 |
| [docs/BACKEND.md](docs/BACKEND.md) | 启动方式、接口细节、错误码、前端联调 |
| [CONTRACT_EXT.md](CONTRACT_EXT.md) | 对 `PROJECT_HANDOFF.md` §8 契约的扩展说明（为什么加字段） |

---

## 已知限制

- 无文字层的 PDF / 图片需要先做 OCR/视觉识别（当前用 `--ocr-cache` 回灌），服务端尚未内置模型。
- `mode=ai` 未接，返回 `503`。
- 机会与资源是演示数据（`source: demo`）。
- 结果为单机文件存储（`var/plans/`），无鉴权、限流、分页。

---

## 与前端集成

1. 把本目录放到仓库根目录，与 `src/` 同级。
2. 前端 `.env.local` 加：`VITE_API_BASE_URL=http://127.0.0.1:8000`
3. 后端起服务，前端 `npm run dev`。

CORS 已允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`；换端口改 `api/devserver.py` 的 `ALLOW_ORIGINS` 与 `api/app_fastapi.py` 的 `allow_origins`。
