# 松果来信 · Pine Letters

团队与 AI 工作区交接请读 [项目技术文档](PROJECT_HANDOFF.md)。

首页展示高清雨夜读书场景。窗外雨丝会落下，咖啡会冒热气，睡着的橘猫会轻轻呼吸，女孩手里的书会间歇翻页。点击那本书即可进入摊开的手帐，从右页的五个贴纸进入各模块。点击「返回目录」可回到目录，点击「回到首页」可回到雨夜读书场景。动效会响应系统的「减弱动态效果」设置。

雨夜首页点击橘猫可打开「校园登录」，窄屏使用右上角的橘猫入口。学号和密码在[中国农业大学综合服务平台](https://one.cau.edu.cn/tp_up/)的官方认证页填写。未接入学校授权时，可以打开官方平台或继续浏览示例手帐。校园联调数据接入后，课程簿和路线图共用同一份学生资料。课程簿分开显示培养方案、周课表、已修学分和本学期在修学分，同步失败和缺失字段会显示对应状态。

成长路线图展示一整张旧纸地图，八个卡通地标可以切换学期。点击「编辑便签」可修改标题、说明与行动清单，也可以勾选行动。初始示例的改动按学期保存在当前浏览器。游客可填写专业、学期和兴趣生成规则路线。校园学业资料接通后，可核对同步的专业、学期和方案版本，填写兴趣生成校园规则路线，再展开便签下方的「查看规划依据」。校园资料、路线及其编辑只保留在当前标签页内存，退出、重新同步或刷新都会清理。真实学校授权、项目校园接口和 AI 服务待后端接通。手机端可左右滑动地图，目标便签在地图下方。

日常手帐使用普通月历。点选日期可以查看当天的任务、成就、心情记录与截止事项。完成当天的全部待办可解锁咖啡贴纸。月历用小贴纸和标签标记已有的心情与 DDL。数据保存在当前浏览器，提醒在打开日常手帐期间显示。首次打开会看到标明的示例数据。

冒险公告栏在 `#/notebook/opportunities`。可以同时按类别和专业筛选，选择专业后仍会保留不限专业的活动。点便签在原页打开详情。当前活动和 B 类等级为示例，官方公告和学校认定目录的链接待接入真实资料。

森林图书馆在 `#/notebook/library`。按课程名或别名查找课程介绍、开课教师、学习经验和历年真题。教师可按学期筛选，真题可按学年及考试类型筛选。当前教师与真题为示例，资料详情在配置文件或平台入口后显示相应操作。

## 在本地运行

需要 Node.js 22.12 或更新版本，安装 Node.js 后会自带 npm。在此文件所在的项目文件夹中运行：

```bash
npm install
npm run dev
```

打开终端显示的本地地址，通常是 `http://localhost:5173/`。改动源文件后，Vite 会刷新页面。用 `Ctrl+C` 停止服务器。

`npm run build` 会检查并生成发布用的 `dist/`。构建后可用 `npm run preview` 在本地预览。

本地校园联调可运行 `npm run dev:campus`，打开 [测试学生选择页](http://127.0.0.1:5186/__campus-preview)，选择「大数据管理与应用」或「理科试验班」。回首页点橘猫进入课程簿，再点「去生成成长路线」。两份资料均为虚构，理科试验班样例的在修学分空缺，可用于检查缺数据状态。此命令仅启动本机预览，无需启动 Python 后端。

联调规则规划时，从团队仓库的 `backend/` 目录运行 `python api/devserver.py --port 8000`，在前端根目录的 `.env.local` 添加 `VITE_API_BASE_URL=http://127.0.0.1:8000`，再用 Vite 默认的 5173 端口启动前端。生成按钮调用 `POST /api/v1/growth-plans` 的演示规则模式，接口见技术文档第 8.4 节。

校园联调时，在项目根目录的 `.env.local` 中设置 `VITE_CAMPUS_API_BASE_URL` 为项目校园后端地址，再重启前端。通过同源代理联调可填 `/`。项目后端负责跳转到学校认证页、处理回跳、维护本站会话、获取授权数据及生成校园规则路线。接口见技术文档第 8.3、8.4 节。

## 文件在哪里

- `src/App.jsx` 处理首页、手帐目录和各模块的路由切换。
- `src/components/EntranceScene.jsx` 放首页插画和书本入口，`ReadingPageTurn.jsx` 负责书页动画。
- `src/components/EntranceAtmosphere.jsx` 放首页窗雨、杯口热气和猫咪呼吸图层。
- `src/components/NotebookDesk.jsx` 放平摊的手帐、目录和桌面动效图层。
- `src/features/courses/` 放课程簿、可按节次渲染的周课表、示例数据和木纹布局。
- `src/features/campus/` 放橘猫登录入口、会话状态和校园数据请求。
- `src/features/trainingPlan/` 放课程簿的培养方案数据适配和清单。
- `src/features/roadmap/` 放地图、八学期数据、可编辑便签和本地存储。
- `src/features/diary/` 放日常手帐、月历、编辑表单、心情记录、贴纸奖励和本地数据。
- `src/features/opportunities/` 放公告栏、详情和示例数据。便签、贴纸和软木板素材位于 `src/assets/opportunities/`。
- `src/features/library/` 放课程检索、资料筛选、详情和示例数据。分类贴纸和纸面素材位于 `src/assets/library/`。
- `src/components/paperSpread.css` 提供课程簿与日常手帐共用的双页纸面和手机单页布局。
- `src/sections.js` 放五个目录项的名称、贴纸位置和说明。
- `src/styles.css` 放纸面排版、热气与呼吸动画、手机适配。

## 插画和字体

首页使用对你提供的参考图进行清晰化后的素材 `src/assets/reading-room-hd.webp`，尺寸为 1858 × 846。旧版参考图保存在 `src/assets/reading-room.jpg`。手帐页使用已确认的书桌插画 `src/assets/notebook-desk.webp` 和贴纸 `src/assets/journal-stickers.webp`。站酷快乐体的网页字体子集随项目保存，覆盖当前标题和目录。

<details>
<summary>首页高清图的 ImageGen 提示词</summary>

> Work as a faithful high-resolution restoration/upscale of the attached illustration. Use the attached image as the ONLY edit target. Deliver the exact same ultrawide composition (original aspect 1484:676, about 2.195:1) at the highest suitable output resolution. Match each object's position and relative scale exactly, pixel aligned if possible, because this will replace an existing website raster background that already has accurately placed interactive regions. This is a crisping and upscale pass, not a redesign or re-illustration. Preserve the girl's pose, hands and expression, auburn ponytail and headphones, absolutely preserve the exact shape, perspective and position of the reddish-brown book she is holding, the window panes and their mullions, sunset buildings, black articulated lamp, orange coffee cup, orange tabby sleeping on the same stack of books at right (same exact contour) and all props. Preserve dark warm palette, low light, rainy peach dusk, exact framing, mostly flat cel shading and very fine original grain. Only clarify and anti-alias the ink outlines, improve fine details and readability of small existing details without inventing new details, gently reduce screenshot resampling artifacts, maintain colors. Preserve drawn rain. Do not add a white border, any letters, controls, UI or symbols. Do not move, replace, restyle, rearrange or crop the character or props. Priority is geometrical and stylistic identity to the supplied art.

</details>
