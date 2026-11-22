# API 契约扩展说明（对应 PROJECT_HANDOFF.md §8）

> 状态：**草案转已确认**（契约扩展走"新增字段"，已与产品负责人确认）
> 影响范围：§7.2 课程簿、§8.2 错误表、§8.3 上传接口、§12 待确认项
> 实现：`backend/ingest.py`（统一入库）、`backend/to_api_v1.py`（映射）、`backend/pdf_adapter.py`、`backend/pdf_raster.py`

## 1. 为什么要改

§8.3 的响应是扁平 `courses[]`，三个东西装不进去：

1. **一门课多个学期**（`3秋2春`）→ `term: int` 只能填一个；
2. **课程组与组要求** → §7.2 要求"各类别要求分别展示"，扁平列表没有"组"这个层级；
3. **分方向方案**（植物模块 75.5 / 动物模块 78.5）→ 没有 `track`，两套学分无法同时表达。

实测两份真实样本都有这三类情况，因此扩展为"新增字段、不动旧字段"，前端可先忽略。

## 2. 响应体新增字段

```jsonc
POST /api/v1/training-plans  →  200
{
  "plan_id": "plan_20261121_001",
  "source": {
    "mode": "parsed",              // demo | parsed（原有）
    "file_name": "智能装备试验班.doc",
    "format": "word97",            // 新增：docx | word97 | pdf_text | pdf_vector | image
    "text_layer": true,            // 新增：文件里有没有可提取的文字
    "ocr_used": false,             // 新增：是否走了图像识别
    "files": null                  // 新增：多文件合并时列出每个来源（单文件为 null）
  },
  "program_name": "工科试验班（智能装备）",
  "cohort": null,
  "parse_status": "complete",      // complete | partial（原有；failed 走 422）
  "courses": [{
    "id": "C015", "code": null, "name": "大学物理实验B",
    "term": 3,                     // 原有：1-8 或 null
    "terms": ["2秋"],              // 新增：原始学期标记（可多个、可"不限"）
    "category": "required",        // 原有：required | elective | practice | other
    "group": "大类平台课程II",      // 新增：所属课程组
    "track": null,                 // 新增：植物模块 | 动物模块 | null
    "credits": 1.5,
    "source_ref": null             // 无法定位页码时为 null，并出 warning
  }],
  "groups": [{                     // 新增：组级要求（§7.2 需要）
    "name": "生命科学大类平台课",
    "module": "大类平台教育",
    "rule": "all_of",              // all_of | credits | pick_n | pick_n_of | candidate_pool | unknown
    "credits_required": { "植物模块": 3.0, "动物模块": 6.0 },
    "computed_credits": 9.0,
    "course_count": 4,
    "practice_credits": null
  }],
  "credit_summary": {
    "parsed_credits": 111.0,          // 原有，口径改为"必修类合计"
    "elective_pool_credits": 39.0,    // 新增：选修课程池大小，**不是**要求学分
    "practice_credits": 0.0,          // 新增：实践环节学分
    "graduation_target_credits": 150.0
  },
  "warnings": [{ "code": "...", "message": "...", "user_action": "..." }],
  "completeness": {                   // 新增：解析完整度与报警
    "level": "full",                  // full | partial | failed
    "score": 100,
    "checks": [{ "key": "courses_found", "ok": true, "detail": "识别到 40 门课程" }],
    "coverage": { "name": { "hit": 40, "total": 40 } },
    "alerts": [{ "code": "NO_TEXT_LAYER", "severity": "high",
                 "message": "...", "user_action": "..." }],
    "recommended_upload": { "format": "docx", "label": "Word 原件（.docx）", "reason": "..." }
  }
}
```

`credit_summary.parsed_credits` 口径必须改：**只累加必修类**。样本二 57 门课累加是 135，但其中 39 是选修池，直接当"已解析学分"会误导。

### 2.1 多文件上传

`POST /api/v1/training-plans` 的 `file` 字段可重复，语义有两种，首版只实现后者：

| 场景 | 语义 | 当前 |
|---|---|---|
| 不同专业的两份方案 | 应是两个 plan（批量） | 未做，前端调两次即可 |
| **同一份方案被拆成多个文件** | 合并成一个 plan | **已实现** |

合并规则：按（课程名, 学分, 课程组）去重；模块/组/子组同名合并；学分逐级重算；
`source.files` 列出每个来源文件名与格式。真实案例就是 A 学院的 8 份 PDF（按课程性质拆分）。

### 2.2 `term` 的归一化（重要）

培养方案里的 `N秋 / N春` 是**学年制**写法，`N` 是学年不是学期：

| 原文 | 1秋 | 1春 | 2秋 | 2春 | 3秋 | 3春 | 4秋 | 4春 |
|---|---|---|---|---|---|---|---|---|
| `term` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |

依据：文档中「毕业设计 4春」在最后、「机械设计基础课程设计 3春」在其前一学年。
按“第 N 学期”直译会把课程全挤到前 4 个学期、后 4 个学期空着。
`courses[].terms` 保留原文，`term` 是归一化后的 1–8 整数。
教务系统导出的纯数字学期（1~11）按学期理解，超过 8 的进 `warnings` 的 `TERM_OUT_OF_RANGE`。

## 3. 完整度判定| check | 通过条件 | 不通过时的含义 |
|---|---|---|
| `courses_found` | 课程数 > 0 | 整份读不出来 |
| `fields_complete` | 课程名 100%，学分 ≥90% | 版式或有识别问题 |
| `credit_target_present` | 文档写了毕业总学分 | 可能只上传了部分文件 |
| `credit_reconciled` | 组要求合计 = 声明总学分 | **有课程或组没被读全** |
| `groups_complete` | 每个组有要求学分或课程合计 | 组结构没还原 |

- `full`：5 项全过且无 error → `parse_status: complete`，HTTP 200
- `partial`：有任一不过 → `parse_status: partial`，HTTP 200（前端提示"部分解析"）
- `failed`：课程数为 0 → **HTTP 422** + 错误信封 `{"error": {"code": "PARSING_FAILED", ...}}`

## 4. 报警码（前端可直接渲染 `user_action`）

| code | severity | 什么时候 | 给用户的话 |
|---|---|---|---|
| `NO_TEXT_LAYER` | high | 无文字层且没有 OCR 结果 | 优先传 Word 原件；PDF 请"另存为"而不是"打印" |
| `OCR_USED` | medium | 走了图像识别 | 结果由识别得到，请抽查学分与学期 |
| `NO_COURSES` | high | 0 门课 | 换 Word 原件重新上传 |
| `FIELDS_INCOMPLETE` | medium | 关键字段缺失 | 补字段或换更规整的文件 |
| `NO_TOTAL_CREDITS` | medium | 文档没写毕业总学分 | 可能只传了部分文件，请传完整方案 |
| `CREDIT_NOT_RECONCILED` | high | 有总学分但对不上 | **有内容没读全**，请用 Word 原件复核 |
| `GROUPS_INCOMPLETE` | medium | 组要求缺失 | 传含模块学分要求的原件 |

## 5. 文件格式优先级（"最能识别的"）

| # | 格式 | 实测 | 说明 |
|---|---|---|---|
| 1 | **`.docx`（Word 原件）** | 有文字层 + 真实表格 | **推荐首选**，字段最全 |
| 2 | `.doc`（Word 97） | 40 门课、学分逐级核平 | 同上，建议另存为 .docx 更稳 |
| 3 | 含文字层的 PDF | 可解析，表格靠坐标还原 | 合并单元格、跨页可能丢行 |
| 4 | 转曲/扫描 PDF | **0 字体对象、0 文本操作符** | 必须转图识别，准确率最低 |
| 5 | 图片（截图/照片） | 无版面结构 | 不建议 |

给用户的操作指引（已写进 `user_action`）：

> **最好的**：在 Word 里打开 → 另存为 → Word 文档（`.docx`）
> **可以的**：Word/Excel → 文件 → 导出 → 创建 PDF（**不要**用"打印 → Microsoft Print to PDF"，也不要截图）

## 6. OCR 接入点

无文字层时 `ingest.py` 会栅格化并产出任务清单：

```json
{ "source": "A专业必修.pdf",
  "pages": ["out/render/A专业必修_p1.png"],
  "schema": { "columns": ["group","code","name","nature","attr","hours","credits","status","earned","term"] } }
```

把每页图交给视觉模型/OCR，按 `columns` 输出 CSV，再用 `--ocr-cache` 回灌即可。
本仓库已用人工识别的缓存跑通 8 份 PDF，即该 seam 的参考实现。

## 7. 认证与学业数据（新增 §8.6）

原文档 §8 只有业务接口，没有登录。这里补一节，编号接在 §8.5 之后。

### 7.1 路由

| 方法 | 路径 | 输入 | 结果 |
|---|---|---|---|
| GET | `/api/v1/auth/login` | 可选 `redirect` | 302 到学校登录页；mock 模式返回 `login_url` |
| GET | `/api/v1/auth/callback` | 学校回跳的 `ticket`（CAS）或 `code` | 302 回前端 + `Set-Cookie: pine_session` |
| GET | `/api/v1/auth/session` | Cookie | `{authenticated, student, source, expires_at}` |
| POST | `/api/v1/auth/logout` | Cookie | 清会话 + 清 Cookie |
| GET | `/api/v1/academic/profile` | Cookie | 学业数据 + 逐字段状态（未登录 401） |
| POST | `/api/v1/academic/import` | 成绩单 CSV / JSON / 文本 | 解析成已修课程并与方案对账 |
| GET | `/api/v1/training-plans/match` | `major`/`enroll_year` 或 `use_session=1` | 匹配到的 `plan_id` 与匹配等级 |

### 7.2 学业数据（逐字段状态）

```json
{
  "student": { "student_id": "2024A001", "name": "林小满" },
  "profile": { "major": "工科试验班（智能装备）", "enroll_year": 2024, "current_term": 3 },
  "timetable": [{ "course": "概率论与数理统计", "weekday": 1, "period": "1-2", "place": "三教 204" }],
  "completed_courses": [{ "name": "一元微积分", "credits": 5, "term": 1, "score": 88 }],
  "field_status": {
    "major":            { "status": "available" },
    "gpa":              { "status": "unavailable", "reason": "本轮不采集绩点，避免不必要地保存敏感成绩" }
  },
  "missing_fields": ["gpa", "class_name", "advisor"],
  "source": "mock"
}
```

**规则**：取不到的字段不是省略，而是 `unavailable` + `reason`，并汇总进 `missing_fields`。
前端读 `missing_fields` 渲染「暂未同步」，不要靠判断空值。

### 7.2.1 导入成绩单（方案 B）

```http
POST /api/v1/academic/import
multipart/form-data：file=<成绩单.csv>
或 application/json：{"completed_courses":[{"name":"一元微积分","credits":5}], "merge":true}
```

| 参数 | 说明 |
|---|---|
| `file` | CSV（带/不带表头）、纯文本（一行一门）、JSON 都认 |
| `merge` | 默认 `true` 合并进已有记录；`false` 覆盖 |
| `plan_id` | 可选；不传则按会话的「专业+年级」自动匹配 |

返回 `matched[] / unmatched[] / credits_earned`。
`unmatched` 不是错误而是提示：可能是方案版本不对或课程别名，前端应让用户确认；
`matched[].fuzzy=true` 表示靠相似度（≥0.85）匹配，需高亮。

数据来源标记 `self_reported`，**优先级高于学校接口与演示数据**。

### 7.3 方案匹配

```json
{ "plan_id": "plan_20261122_b6a1a6", "match": "exact",
  "plan": { "major": "工科试验班（智能装备）", "cohort": 2024, "course_count": 40 },
  "warnings": [], "queried": { "major": "...", "enroll_year": 2024 } }
```

| `match` | 含义 | 前端动作 |
|---|---|---|
| `exact` | 专业 + 年级都对上 | 直接用 |
| `same_major_nearest_year` | 同专业、用了最接近的年级 | 显示 `warnings`，「这版可能不是你这一届的」 |
| `same_major_any_year` | 同专业但没登记年级 | 提示版本不确定 |
| `none` | 没收录 | 引导上传培养方案（`available_majors` 列出已有专业） |

方案上传时用表单字段 `cohort` 登记入学年份，匹配才有依据。

### 7.4 路线接入学业数据

`POST /api/v1/growth-plans` 新增：

| 字段 | 说明 |
|---|---|
| `use_session` | `true` 时用当前会话的学业数据；未传 `plan_id` 则先按专业+年级匹配 |
| `completed_courses` | 覆盖会话里的已修课程，用于「临时试试别的组合」 |

行为变化（规则版）：
- 已修课程从本学期待办中扣除（例：8 门 → 4 门）
- 已修完的学期，目标改为「复盘 + 巩固」
- 课程组缺口按「已修多少 / 还差多少」计算，而不是「方案排了多少」

`summary` 新增 `based_on`（`academic` / `plan_only`）、`completed_count`、`unmatched_completed`。

## 8. 对原文档的修改建议

| 位置 | 改成 |
|---|---|
| §7.2 "从可选取文字的 PDF 样本开始" | "先做文字层探测；无文字层的样本也要覆盖，走识别分支并报警" |
| §8.2 状态表 | 增加 `422 PARSING_FAILED`（0 门课）；`415` 仅用于扩展名不支持 |
| §8.3 字段表 | 补 `terms` / `group` / `track` / `groups[]` / `completeness` / `cohort` |
| §8 结尾 | 新增 §8.6 认证与学业数据（见本文第 7 节） |
| §12 待确认 | "实际支持的文件类型" 已有答案：docx/doc/pdf/图片，优先级见第 5 节；"学校是否开放统一认证"见 `docs/SCHOOL_AUTH.md` |
