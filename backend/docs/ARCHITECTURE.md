# 后端技术文档 · 松果来信 Pine Letters

> 范围：培养方案解析 → 结构化数据 → 成长路线生成的完整后端链路。
> 对应 `PROJECT_HANDOFF.md` 的 BE-01 / BE-02 / BE-03，以及 BE-04 的接口部分。
> 读者：接手后端的人、接前端的人、以及在各自工作区协作的 AI。

---

## 1. 这个后端做什么

一句话：**把学校给的培养方案（Word / PDF / 图片）变成前端能直接渲染的结构化课程数据，并据此生成四年成长路线。**

它不干的事：不做页面、不管视觉、不做登录、不存用户账号。前端是独立的 React 应用（Vite，默认 5173），通过 `/api/v1` 取数据。

```
前端 (React, :5173)  ──HTTP/JSON──▶  后端 (Python, :8000)  ──▶  培养方案文件
        ▲                                    │
        └────────  routes /api/v1/*  ─────────┘
```

---

## 2. 30 秒上手

```bash
cd backend

# 方式 A：零依赖，立刻能跑（推荐先用这个）
python api/devserver.py --port 8000
#   或 Windows 双击 start_api.bat

# 方式 B：FastAPI（装上依赖后，路由与 A 完全一致）
pip install -r requirements.txt
uvicorn api.app_fastapi:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/> 是接口清单；打开 <http://127.0.0.1:8000/ui> 是内部核对页（可以拖文件上传看结果）。

命令行跑完整条链路：

```bash
python pipeline.py "培养方案.docx"
# → out/api/plan.json   （接口响应体）
# → out/pipeline_report.md（人看的报告）
```

---

## 3. 目录结构

```text
backend/
├── pipeline.py              一条命令跑完整条工作流（CLI 入口）
├── ingest.py                ★ 统一入库：格式探测 → 适配器 → 完整度 → 报警
├── to_api_v1.py             ★ 映射成 /api/v1/training-plans 的响应体
│
├── curriculum_parser.py     Word 解析内核（抽取/建表/归一化/校验）
├── pdf_adapter.py           PDF 抽取适配器（对象流/ToUnicode/坐标聚行）
├── pdf_raster.py            无文字层 PDF 的栅格化兜底（numpy + Pillow）
├── assemble_course_list.py  第二种数据形态：教务"课程体系明细"导出
│
├── report.py                curriculum.json → 人看的解析报告
├── gaps.py                  缺口分析（给定方向 + 已修课程）
├── verify_formats.py        格式矩阵自检（六种输入 × 完整度/HTTP）
│
├── api/
│   ├── handlers.py          ★ 业务层（与框架无关，返回 (status, body)）
│   ├── growth.py            ★ 成长路线生成 + 结构校验
│   ├── devserver.py         零依赖 HTTP 服务（当前主力）
│   ├── app_fastapi.py       FastAPI 入口（同一批 handlers）
│   ├── fixtures.py          机会/资源演示数据（source: demo）
│   ├── ui.html              内部核对页（不是产品页面）
│   └── smoke_test.py        接口冒烟测试（22 项）
│
├── docs/
│   ├── ARCHITECTURE.md      本文
│   └── BACKEND.md           启动、接口、错误码、联动步骤
├── CONTRACT_EXT.md          给 PROJECT_HANDOFF.md §8 的契约扩展说明
├── requirements.txt
├── start_api.bat            Windows 一键启动
└── out/                     ★ 产物（不进 git 的只有 var/）
```

---

## 4. 架构：三层

```
┌──────────────────────────────────────────────────────────┐
│ API 层        devserver.py / app_fastapi.py               │
│               只做 HTTP 翻译：多部分解析、状态码、CORS     │
├──────────────────────────────────────────────────────────┤
│ 业务层        handlers.py / growth.py / to_api_v1.py      │
│               与框架无关，返回 (status, body dict)          │
├──────────────────────────────────────────────────────────┤
│ 解析层        ingest.py（调度）                            │
│               ├─ curriculum_parser.py   Word 内核          │
│               ├─ pdf_adapter.py         PDF 文本           │
│               ├─ pdf_raster.py          无文字层→图        │
│               └─ assemble_course_list.py 教务导出形态      │
└──────────────────────────────────────────────────────────┘
```

**为什么这样分**：解析层的每一次崩溃都不该影响 API 的形状；换 Web 框架（FastAPI ↔ 标准库 ↔ 以后的别的）时业务层一行不改。`api/handlers.py` 里没有任何 `import fastapi`。

---

## 5. 数据流（一条链，五步）

```
① 文件
   │  detect()：看扩展名 + 二进制特征
   ▼
② 格式判定
   docx / word97 / pdf_text / pdf_vector / image
   │  文本层？字体对象数 / 文本操作符数
   ▼
③ 抽取（适配器，输出统一的 "段落 + 单元格" 事件流）
   Word      →  OLE2 → WordDocument 流 → piece table
   docx      →  zip → word/document.xml → w:tbl / w:p
   pdf_text  →  PDF 对象流 → 内容流解释 → 按 y 聚行、按 gap 切列
   pdf_*     →  无文字层：栅格化（pdf_raster）→ 交给 OCR/视觉
   │
   ▼
④ 解析内核（curriculum_parser.Parser）
   标题建模块 → "XX：N 学分" 建组 → 表格行建课程
   → 归一化（类型/学时/学期）→ 实践表归集 → 逐级对账
   │
   ▼
⑤ 输出
   curriculum.json（内部结构）──to_api_v1──▶ plan.json（接口响应体）
   + completeness（完整度/报警/建议上传格式）
```

**关键点**：第 ③ 步的四种适配器输出**同一种中间表示**，所以第 ④ 步的解析内核完全不知道文件是什么格式。

---

## 6. 数据模型

### 6.1 内部结构 `curriculum.json`

```jsonc
{
  "meta": { "major_name": "...", "degree": "工学学士", "duration_years": 4,
            "total_credits": 150, "general_credits": 44, "practice_credits_declared": 38.25 },
  "modules": [{
    "id": "M1", "name": "通识教育", "credits_required": 44,
    "groups": [{
      "id": "M1.G1", "name": "思政类", "credits_required": 18,
      "computed_credits": {"植物模块": 18, "动物模块": 18},
      "subgroups": [{
        "name": "思想政治理论必修课", "credits_required": 16.5,
        "courses": [{ "id": "C001", "code": "12314001", "name": "Academic Writing（1）",
                      "type": "required", "credits": 2.0, "terms": ["1秋"],
                      "hours": {"theory": 32, "practice": 0}, "track": null }]
      }]
    }]
  }],
  "courses": [ /* 拍平后的课程，带 module/group/subgroup 路径 */ ],
  "issues": [ { "level": "error|warning|info", "code": "...", "message": "..." } ]
}
```

三个必须理解的概念：

| 概念 | 含义 | 为什么需要 |
|---|---|---|
| `credits_required` 可以是数字**或字典** | `{"植物模块": 75.5, "动物模块": 78.5}` | 同一份方案有两条培养方向，学分要求不同 |
| `track` | 课程的软标签：`植物模块` / `动物模块` / `工程模块` | 方向互斥靠标签过滤，不靠写死；`工程模块` 不在方向集合里，因此对所有方向都计入 |
| `rule` | 组规则：`all_of` / `credits` / `pick_n` / `pick_n_of` / `candidate_pool` | 区分"全部必修"和"从池子里选够学分" |

### 6.2 接口响应 `plan.json`

完整定义见 `CONTRACT_EXT.md`。相比 `PROJECT_HANDOFF.md` §8.3 的草案，扩展了三处（都是**新增字段**，旧前端可忽略）：

- `courses[].terms` / `group` / `track`
- `groups[]`（组级要求与规则）
- `completeness`（完整度、报警、建议上传格式）+ `credit_summary.elective_pool_credits`

### 6.3 两个口径，别混

| 字段 | 含义 | 陷阱 |
|---|---|---|
| `credit_summary.parsed_credits` | **必修类**课程学分合计 | 不能拿"所有课程累加"当毕业进度 |
| `credit_summary.elective_pool_credits` | **选修课程池**大小 | 池子大小 ≠ 要求学分（A 学院样本：池 39，实际只需选其中一部分） |

---

## 7. 关键设计决策（每条都有代价）

### 7.1 课程行识别用"学分锚点法"，不依赖列序

不同学校的表头顺序、列数、合并单元格都不一样。做法是：**以"学分"这一格为锚点**，向前校验 4 格（学时/类别/单位/名称）、向后校验 1 格（学期），全部符合形态才认定是一行。

代价：形态校验是启发式的，遇到"学时列混入周数"这类脏数据会漏行。所以每次解析都有 `fields_complete` 检查兜底。

### 7.2 `N秋 / N春` 是学年制，不是学期制

**这是本项目踩过最大的坑。** 培养方案写 `2秋`，意思是**第二学年秋季 = 第 3 学期**，不是第 2 学期。

证据：文档里"毕业设计 4春"在最后、"机械设计基础课程设计 3春"在其前一学年。按"第 N 学期"直译会把课程全挤进前 4 学期、后 4 学期空着。

归一化规则（`to_api_v1.parse_term`）：

| 原文 | 1秋 | 1春 | 2秋 | 2春 | 3秋 | 3春 | 4秋 | 4春 |
|---|---|---|---|---|---|---|---|---|
| `term` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |

`courses[].terms` 保留原文，`term` 是归一化后的整数。教务系统导出的纯数字学期（1~11）按学期理解，超过 8 的进 `TERM_OUT_OF_RANGE` 报警。

### 7.3 实践学分表是"投影"，不是新课程

培养方案末尾常有一张"实践教育环节"表，把同一批课程再列一遍（只算实践部分学分）。如果当成新课程，学分会翻倍。

做法：`resolve_practice()` 把实践表的行**按课程名挂回主课程**（`practice_credits` 字段），名字对不上的按相似度匹配并报警，仍对不上就落到课组级。

### 7.4 完整度是五个检查项，不是一句"成功"

| 检查 | 通过条件 | 不过意味着 |
|---|---|---|
| `courses_found` | 课程数 > 0 | 整份读不出来 → HTTP 422 |
| `fields_complete` | 课程名 100%、学分 ≥90% | 版式或识别有问题 |
| `credit_target_present` | 文档写了毕业总学分 | 可能只上传了部分文件 |
| `credit_reconciled` | 组要求合计 = 声明总学分 | **有内容没被读全** |
| `groups_complete` | 每组有要求学分或课程合计 | 组结构没还原 |

只有五项全过才是 `full`。**"看起来解析成功"和"真的读全了"是两件事**，这个区分是这个后端最核心的产品价值。

### 7.5 多文件 = 一份方案

真实场景：A 学院把一份培养方案按课程性质拆成了 **8 个 PDF**。

`POST /api/v1/training-plans` 的 `file` 字段可重复，多个文件**合并成一份 plan**：按（课程名, 学分, 课程组）去重，模块/组/子组同名合并，学分逐级重算，`source.files` 保留来源清单。传同一份两遍不会翻倍（40 门还是 40 门）。

### 7.6 无文字层 PDF：先探测，再降级，绝不静默失败

实测样本里 **8 份 PDF 全部 0 个字体对象、0 个文本操作符**——文字被转成了矢量路径，任何文本库都读不出内容。

链路：`detect()` 命中 → `pdf_raster` 栅格化 → 交给 OCR/视觉 → 回灌。没有 numpy/Pillow 时降级为"只登记识别任务 + `RENDER_DEPS_MISSING` 报警"，不会抛 500。

### 7.7 合格的文件格式排序

| # | 格式 | 实测 | 说明 |
|---|---|---|---|
| 1 | **`.docx`（Word 原件）** | 有文字层 + 真实表格 | 首选 |
| 2 | `.doc` | 40 门课、学分逐级核平 | 建议另存为 .docx |
| 3 | 含文字层 PDF | 可解析，表格靠坐标 | 合并单元格/跨页可能丢行 |
| 4 | 转曲/扫描 PDF | 0 字体 0 文本 | 必须图像识别 |
| 5 | 图片 | 无版面结构 | 不建议 |

---

## 8. 支持格式与实测矩阵

`python verify_formats.py` 可复现：

| 场景 | 格式 | 文字层 | 课程 | 学分核平 | 完整度 | HTTP | 报警 |
|---|---|---|---|---|---|---|---|
| Word `.doc`（真实培养方案） | word97 | 有 | 40 | ✓ | full 100% | 200 | — |
| Word `.docx`（不完整样本） | docx | 有 | 5 | ✗ | partial 80% | 200 | `CREDIT_NOT_RECONCILED` |
| 文字层 PDF（非培养方案） | pdf_text | 有 | 0 | ✗ | failed 0% | 422 | `NO_COURSES` |
| 无文字层 PDF（无识别） | pdf_vector | 无 | 0 | ✗ | failed 0% | 422 | `NO_TEXT_LAYER` |
| 无文字层 PDF（带识别） | pdf_vector | 无 | 14 | ✗ | partial 60% | 200 | `OCR_USED` |
| 图片 | image | 无 | 0 | ✗ | failed 0% | 422 | `NO_TEXT_LAYER` |

---

## 9. 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 接口清单页（开发工具） |
| GET | `/ui` | 内部核对页（开发工具，上线前删） |
| GET | `/healthz` | 可用性 |
| POST | `/api/v1/training-plans` | 上传解析，`file` 可重复 |
| GET | `/api/v1/training-plans/{plan_id}` | 读回上次结果 |
| POST | `/api/v1/growth-plans` | 生成八学期路线（`mode=demo\|ai`） |
| GET | `/api/v1/opportunities`、`/{id}` | 机会（当前为 fixture） |
| GET | `/api/v1/resources`、`/{id}` | 资源（当前为 fixture） |

错误统一信封（§8.2）：

```json
{ "error": { "code": "...", "message": "...", "request_id": "req_...", "details": [] } }
```

| 状态 | code | 场景 |
|---|---|---|
| 400 | `EMPTY_FILE` | 空文件 |
| 404 | `NOT_FOUND` / `PLAN_NOT_FOUND` | 路径或记录不存在 |
| 413 | `FILE_TOO_LARGE` | 超过 20 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | 扩展名不支持 |
| 422 | `MISSING_FILE` / `PARSING_FAILED` / `INVALID_MODE` | 参数或解析失败 |
| 502 | `GROWTH_INVALID` | 路线未过结构校验 |
| 503 | `AI_NOT_CONFIGURED` | AI 未配置 |

---

## 10. 成长路线（BE-03）

`api/growth.py` 两层：

1. **rule**（`mode=demo`）：确定性生成。每学期目标 = 该学期课程 + 学分缺口 + 兴趣实践。
   缺口 = 组要求 − 方案内已排课程；只把最大的 6 条做成目标并摊到 3–7 学期，其余放 `summary.groups_with_gap`。
2. **ai**（`mode=ai`）：未配置，返回 503。接入点已留好，输出必须过同一个 `validate()`。

**返回前必过结构校验**：学期 1–8 有序、goal id 唯一、`course_ids` 都能在方案里找到、标题 ≤60 字、actions ≤5 条。不过就 `502`，不给前端坏数据。

---

## 11. 测试

```bash
python api/smoke_test.py http://127.0.0.1:8000   # 22 项接口测试
python verify_formats.py                          # 6 种输入的格式矩阵
python pipeline.py "样本.docx"                     # 端到端
```

当前：**22/22 通过**。覆盖正常上传、多文件合并、读回、路线结构、404/422/503、无文字层降级。

---

## 12. 已知限制

| 项 | 现状 | 后面怎么办 |
|---|---|---|
| 视觉/OCR | 无文字层文件需要人工识别后回灌（`--ocr-cache`） | 接视觉模型，输出同一份 CSV schema |
| AI 路线 | `mode=ai` 返回 503 | 接模型 + 复用 `validate()` |
| 机会/资源 | `api/fixtures.py` 的演示数据 | 资料同学给真实数据后替换 |
| 存储 | `var/plans/*.json` 落盘 | 换数据库时只改 `handlers.py` 的存取层 |
| 鉴权/限流/分页 | 未做 | 上线前 |
| 课程代码缺失 | 样本 40 门里只有 4 门有编号 | 用（名称+学分+学期）做指纹 |

---

## 13. 给新人 / AI 的阅读顺序

按这个顺序读，30 分钟能建立完整心智模型：

1. 本文 §1–§5（做什么、怎么跑、数据怎么流）
2. `ingest.py` 的 `detect()` 和 `ingest_many()` —— 整个调度在这里
3. `to_api_v1.py` 的 `convert()` —— 内部结构怎么变成接口
4. `curriculum_parser.py` 的 `Parser.__init__` / `try_row` / `validate` —— 解析内核
5. `api/handlers.py` —— 每个路由对应一个函数，一一对应
6. `CONTRACT_EXT.md` —— 契约为什么扩展、扩展了什么
7. `docs/BACKEND.md` —— 启动与联调细节

**改代码前的三条纪律**（来自 `PROJECT_HANDOFF.md` §10）：

- 改接口字段 → 同步改 `to_api_v1.py`、`CONTRACT_EXT.md`、`smoke_test.py`
- 改解析逻辑 → 跑 `verify_formats.py`，六种输入的判定不能退化
- 新增报警码 → 在 `ingest.assess()` 里加，并写清 `user_action`（这是给用户看的话）

---

## 14. 术语表

| 词 | 含义 |
|---|---|
| 模块 module | 培养方案的一级分类（通识教育 / 大类平台教育 / 专业教育 / 实践教育环节） |
| 课程组 group | 模块下的学分单元（思政类 18 学分、学院平台课 30.5 学分） |
| 子组 subgroup | 组内的细分（思想政治理论必修课 16.5 / 马理论选修 0 / 社会实践 1.5） |
| track | 培养方向标签（植物模块 / 动物模块）；也用于"必修但可置换"的模块组 |
| rule | 组规则：全修 / 修满学分 / 选 N 门 / M 选 N / 候选池 |
| term | 归一化后的学期号 1–8（注意：原文 `2秋` = 3） |
| 选修池 | 选修课可选范围的学分总和，**不等于**要求学分 |
| 完整度 completeness | 五项检查 + 报警 + 建议上传格式，决定 `parse_status` 与 HTTP 码 |
