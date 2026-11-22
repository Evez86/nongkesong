# 松果来信 · Render 公网演示

这个分支把 Vite 前端和团队的 Python 规则规划放在同一个 Web Service。Dockerfile 会构建前端并配置同源 `/api/v1/growth-plans`，FastAPI 在同一个端口返回网页和 API。

## 创建 Web Service

1. 在 Render 项目中选择 **New → Web Service**。
2. 选择 **Git Provider**，授权 GitHub 仓库 `Evez86/nongkesong`。
3. 核对下列配置后创建服务。

| 设置 | 填写值 |
| --- | --- |
| Name | 自定，例如 `pine-letters-demo` |
| Branch | `deploy/competition-demo` |
| Language | `Docker` |
| Root Directory | 留空，从仓库根目录构建 |
| Dockerfile Path | `./Dockerfile` |
| Docker Command | 留空，使用 Dockerfile 的 `CMD` |
| Health Check Path | `/healthz` |

竞赛演示无需添加环境变量。Dockerfile 会读取 Render 设置的 `PORT`。选择 **Free** 时，服务在闲置后首次访问需要等待唤醒。

## 验收及更新

1. 部署状态显示 **Live** 后，在无痕窗口打开服务页面显示的 HTTPS 首页地址。
2. 点女孩手里的书进入目录。选择「成长路线图」并点「生成我的路线」。填写专业，选大一下，填写一个兴趣方向。确认便签出现对应的规则目标。
3. 将首页地址填入赛事 Demo 字段。在源码材料中记录与线上部署一致的提交。
4. 队友完成新功能后，将已验证的改动同步到此部署分支，再在原 Render 服务部署新版。继续使用已有的首页地址。

当前公开演示使用游客规则路线，校园认证、个人学业数据和 AI 生成待接通。培养方案上传解析由团队在内部环境验证。

[Render Web Services](https://render.com/docs/web-services) · [Docker 部署文档](https://render.com/docs/docker)
