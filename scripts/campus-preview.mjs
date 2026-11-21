import { randomUUID } from 'node:crypto';
import { createServer } from 'vite';

const host = '127.0.0.1';
const port = 5186;
const origin = `http://${host}:${port}`;
const picker = '/__campus-preview';
const apiPrefix = '/api/v1/campus/';
const cookieName = 'pine_fixture_student';
const samples = {
  a: {
    name: '测试学生 A', major: '大数据管理与应用', cohort: 2025, term: 3,
    earned: 38, inProgress: 17, target: 150, course: '数据库原理', lab: '数据库实验',
  },
  b: {
    name: '测试学生 B', major: '理科试验班', cohort: 2024, term: 5,
    earned: 72, inProgress: null, target: 144, course: '大学物理', lab: '大学物理实验',
  },
};

const options = Object.entries(samples).map(([id, student]) => `
  <form method="post" action="${picker}/${id}">
    <button>${student.name} · ${student.major}</button>
  </form>`).join('');
const loginPage = `<!doctype html>
<html lang="zh-CN">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>松果来信 · 校园联调</title>
  <style>
    body { margin: 0; background: #443126; color: #4f3426; font: 16px/1.7 system-ui, sans-serif; }
    main { max-width: 480px; margin: 12vh auto; padding: 28px; background: #faebce; border-radius: 8px; }
    button { margin: 5px 0; padding: 9px 14px; border: 1px solid #785238; border-radius: 5px;
      color: #fff1d8; background: #785238; font: inherit; cursor: pointer; }
    a { color: #64432d; }
    @media (max-width: 550px) { main { margin-inline: 15px; } }
  </style>
  <main>
    <h1>松果来信 · 校园联调</h1>
    <p>这里使用两份虚构学生资料。直接选一份体验，无需学号或密码。</p>
    ${options}
    <a href="/">返回首页</a>
  </main>
</html>`;

function json(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(body));
}

function redirect(res, url, cookie) {
  res.writeHead(303, { Location: url, 'Cache-Control': 'no-store', ...(cookie ? { 'Set-Cookie': cookie } : {}) });
  res.end();
}

function academicData(student, planId, courseId) {
  return {
    source: 'demo',
    profile: { program_name: student.major, cohort: student.cohort, current_term: student.term },
    credit_progress: { earned_credits: student.earned, in_progress_credits: student.inProgress },
    training_plan: {
      plan_id: planId, program_name: student.major, cohort: student.cohort,
      version: `${student.cohort} 版 · 联调样例`, parse_status: 'partial',
      courses: [{ id: courseId, name: student.course, term: student.term, credits: 3, category: 'required' }],
      credit_summary: { parsed_credits: 3, graduation_target_credits: student.target },
    },
    timetable: {
      term_label: '联调周课表', weekdays: ['周一', '周二', '周三', '周四', '周五'],
      period_count: 12, evening_start: 9,
      meetings: [{ day: 2, start: 10, end: 11, title: student.lab, room: '测试教室', tone: 'oak' }],
    },
  };
}

function growthPlan(student, planId, courseId, interests) {
  const goal = {
    title: `安排${student.course}的学习进度`,
    actions: ['核对本学期的选课记录', ...interests.slice(0, 1).map((interest) => `预留一次${interest}练习`)],
    course_ids: [courseId],
    basis: `已修 ${student.earned} 学分，距毕业总学分还差 ${student.target - student.earned} 学分。`,
  };
  return {
    id: randomUUID(), source: 'demo', plan_id: planId,
    terms: Array.from({ length: 8 }, (_, index) => ({
      term: index + 1, goals: index + 1 === student.term ? [goal] : [],
    })),
  };
}

async function campusPreview(req, res, next) {
  const { pathname } = new URL(req.url, origin);
  if (pathname === picker && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    return res.end(loginPage);
  }
  const selection = pathname.startsWith(`${picker}/`) ? pathname.slice(picker.length + 1) : '';
  if (req.method === 'POST' && Object.hasOwn(samples, selection)) {
    return redirect(res, '/', `${cookieName}=${selection}; HttpOnly; SameSite=Strict; Path=/`);
  }
  if (!pathname.startsWith(apiPrefix)) return next();

  const endpoint = pathname.slice(apiPrefix.length);
  if (endpoint === 'login') return redirect(res, picker);
  const account = (req.headers.cookie ?? '').match(/(?:^|;\s*)pine_fixture_student=([ab])(?:;|$)/)?.[1];
  const student = samples[account];
  if (!student) return json(res, 401, { error: { code: 'SESSION_REQUIRED' } });
  if (endpoint === 'session') return json(res, 200, { authenticated: true, display_name: student.name, source: 'demo' });

  const planId = `test-plan-${account}`;
  const courseId = `${account}-course`;
  if (endpoint === 'academic-data') {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return json(res, 200, academicData(student, planId, courseId));
  }
  if (endpoint === 'growth-plans' && req.method === 'POST') {
    let raw = '';
    for await (const chunk of req) {
      raw += chunk;
      if (raw.length > 4096) return json(res, 413, {});
    }
    try {
      const { interests } = JSON.parse(raw);
      if (!Array.isArray(interests) || !interests.every((interest) => typeof interest === 'string')) {
        return json(res, 422, {});
      }
      return json(res, 200, growthPlan(student, planId, courseId, interests));
    } catch {
      return json(res, 400, {});
    }
  }
  if (endpoint === 'logout' && req.method === 'POST') {
    res.writeHead(204, { 'Set-Cookie': `${cookieName}=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/`, 'Cache-Control': 'no-store' });
    return res.end();
  }
  return json(res, 404, {});
}

process.env.VITE_CAMPUS_API_BASE_URL = '/';
process.env.VITE_API_BASE_URL = '';
const server = await createServer({
  configFile: false,
  server: { host, port, strictPort: true },
  plugins: [{ name: 'pine-campus-preview', configureServer(vite) { vite.middlewares.use(campusPreview); } }],
});
await server.listen();
console.log(`校园联调预览 ${origin}${picker}`);
