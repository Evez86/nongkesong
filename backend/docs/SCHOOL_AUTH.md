# 学业数据接入方案（三级）

> 结论先行：**不依赖学校审批也能把产品跑完整。**
> 默认走「学生自己导入成绩单」，学校统一认证作为将来可选项，代码已就绪但不阻塞任何验收。

## 1. 为什么不是「必须打通学校」

打通统一认证需要信息中心批准 `service` 回调地址、书面授权代理访问教务，还要处理验证码、密码加密、登录风控。审批周期不可控，而项目要交付。

更关键的是：**让学生把学号密码交给第三方，本身就有法律风险**（个人信息保护法里的敏感个人信息处理）。学生项目不该背这个。

所以拆成三级，按可得性降级，产品功能不缩水：

| 级别 | 做法 | 依赖 | 状态 |
|---|---|---|---|
| **A 手动填报** | 学生自己勾选已修课程 | 无 | ✅ 可用 |
| **B 导入成绩单**（默认） | 从教务系统「导出成绩单/课表」→ 上传 CSV/JSON/文本 → 自动对账 | 无 | ✅ 已实现 |
| C 授权同步 | 统一认证 + 教务接口 | 学校审批 | ⏸ 代码就绪，等审批 |

---

## 2. 方案 B 怎么用

学生从教务系统导出成绩单（多数学校都支持导出 Excel/CSV），另存为 CSV，上传到课程簿。
支持三种输入，格式不对也能兜住：

| 输入 | 例子 | 说明 |
|---|---|---|
| CSV（带表头） | `课程名称,学分,修读学期,成绩` | 列名支持 课程名/课程/名称/学历分/学分/学期/成绩 等别名 |
| CSV（无表头） | `一元微积分,5,88` | 按位置猜：第 1 列课程名，第一个数字是学分 |
| 粘贴文本 | 一行一门：`一元微积分 5 88` | 逗号/空格/制表符都行 |
| JSON | `{"completed_courses":[{"name":"一元微积分","credits":5}]}` | 前端直接调接口时用 |

接口：

```http
POST /api/v1/academic/import
Content-Type: multipart/form-data     # 或 application/json
Cookie: pine_session=<会话>

file=<成绩单.csv>  或  {"completed_courses":[...], "merge": true}
```

返回里最关键的是 **匹配结果**：

```json
{
  "source": "self_reported",
  "imported": 4,
  "total_after_merge": 4,
  "matched": [
    { "name": "一元微积分", "course_id": "C011", "plan_name": "一元微积分",
      "credits": 5.0, "score": 88, "fuzzy": false }
  ],
  "unmatched": [
    { "name": "这门课不存在", "reason": "培养方案里找不到同名课程" }
  ],
  "credits_earned": 12.0,
  "summary": { "matched_count": 3, "unmatched_count": 1, "fuzzy_matched": [] }
}
```

- `unmatched` 不是错误，是**提示**：可能是培养方案版本不对，也可能是选课系统里的别名，学生自己判断
- `fuzzy: true` 表示靠相似度匹配上的（≥0.85），前端应高亮让人确认

导入的数据存在 `var/academic/<学号>.json`，来源标记 `self_reported`，**优先级高于演示数据**。
`GET /api/v1/academic/profile` 的 `source` 会变成 `self_reported`，前端显示「你导入的」。

---

## 3. 对路线的影响（规则版验收）

导入后 `POST /api/v1/growth-plans {use_session: true}`：

| 变化 | 例子（实测） |
|---|---|
| 已修课程从本学期待办里扣除 | 第一学期 8 门 → 4 门 |
| 学分缺口改为「已修多少 / 还差多少」 | 已修 12.0 学分，按组算缺口 |
| 已修完的学期，目标变成复盘/巩固 | 不再提示「完成本学期的课」 |

验收脚本：`python api/verify_auth.py <base_url>`，25 项，含导入与对账。

---

## 4. 学校哪天开放了，怎么切

代码里已有 CAS 实现，切换只改环境变量，不动业务代码：

```bash
PINE_AUTH_MODE=cas
PINE_CAS_LOGIN_URL=https://<学校>/cas/login
PINE_CAS_VALIDATE_URL=https://<学校>/cas/serviceValidate
PINE_APP_BASE_URL=https://<我们的域名>
PINE_ACADEMIC_MODE=file      # 先接学校导出的批量 JSON
PINE_ACADEMIC_SOURCE=/path/to/academic.json
```

数据来源优先级：**导入（self_reported） > 学校导出/接口 > 演示数据**。学生自己确认过的数据永远排最前。

---

## 5. 如果将来要谈，需要确认什么

给信息中心/教务处的问题清单（现在不必谈，存档备用）：

| # | 确认什么 |
|---|---|
| 1 | 统一认证是否对外开放（CAS/OAuth2），能否注册 `service` 回调地址 |
| 2 | 回调地址是否需白名单/备案/校内 IP，是否必须 https |
| 3 | 是否有教务数据接口（专业、年级、学期、课表、已修） |
| 4 | 若无接口，是否书面允许「学生授权后服务端代理访问」 |
| 5 | 学号/成绩的保存期限与展示范围 |
| 6 | 竞赛/科研公告是否有 RSS 或开放接口 |

参考资料：
- [中国农业大学信息化办公室 · 服务一览](https://io.cau.edu.cn/col/col40785/)
- [综合教务管理系统说明](http://jwc.cau.edu.cn/module/download/downfile.jsp?filename=ab835cfd943a47f2be0ddab53fca753e.pdf)

---

## 6. 安全与合规（当前实现）

- 不接收、不存储学校密码（导入的是学生自己导出的成绩单，不是登录凭据）
- 会话 8 小时过期，Cookie `HttpOnly; SameSite=Lax`
- 导入数据只存在部署机器本地 `var/academic/`，不入 git（已在 `.gitignore`）
- 绩点等不必要字段不采集（`field_status.gpa = unavailable`）
- 提供退出与覆盖导入（`merge: false`），学生可随时清空重来
