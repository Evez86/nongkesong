export const categories = [
  ['all', '全部'],
  ['competition', '竞赛'],
  ['research', '科研'],
  ['practice', '实践'],
];

export const majors = [
  ['data-science', '数据科学与大数据技术'],
  ['statistics', '统计学'],
  ['computing', '计算机类'],
  ['environment', '环境科学类'],
  ['design', '设计类'],
];

const demoRecognition = (level) => ({
  level, edition: '2026 年（示例）', title: '学校竞赛认定目录（示例）',
});

const sampleOpportunities = [
  {
    id: 'demo-data-challenge', title: '校园数据分析挑战赛', category: 'competition',
    paper: 'cat', sticker: 'trophy', organizer: '校园创新中心',
    majors: ['data-science', 'statistics', 'computing'],
    deadline_at: '2026-12-04T22:00:00+08:00',
    eligibility: '在校本科生，2–4 人组队。',
    description: '组队完成一份校园主题的数据分析报告，提交数据可视化和简短的分析说明。',
    recognition: demoRecognition('B'),
  },
  {
    id: 'demo-lab-assistant', title: '实验室科研助理招募', category: 'research',
    paper: 'cloud', sticker: 'flask', organizer: '数据分析实验室',
    majors: ['data-science', 'statistics', 'computing'],
    deadline_date: '2026-12-08',
    eligibility: '有基础编程或统计知识的在校本科生。',
    description: '协助整理实验记录、清洗数据，参加每周一次的项目讨论。',
  },
  {
    id: 'demo-winter-volunteer', title: '社区冬日志愿行动', category: 'practice',
    paper: 'postcard', sticker: 'envelope', organizer: '校园志愿服务队',
    openToAllMajors: true,
    deadline_date: '2026-12-12',
    eligibility: '在校学生均可报名，需参加一次岗前培训。',
    description: '参与社区冬日服务，协助整理捐赠物资与现场引导。',
  },
  {
    id: 'demo-ecology', title: '校园生态观察计划', category: 'research',
    paper: 'leaf', organizer: '校园生态课题组',
    majors: ['environment', 'data-science'],
    deadline_date: '2026-12-15',
    eligibility: '在校本科生，能参与两次校园观测。',
    description: '记录校园树木、鸟类和天气变化，整理成可共享的观测笔记。',
  },
  {
    id: 'demo-poster', title: '创意海报设计赛', category: 'competition',
    paper: 'ticket', organizer: '校园文化活动组',
    openToAllMajors: true,
    deadline_date: '2026-12-18',
    eligibility: '在校学生均可参赛，作品须为原创。',
    description: '为校园公共空间设计一张主题海报，并附上简短的创作说明。',
  },
  {
    id: 'demo-market', title: '校园市集志愿招募', category: 'practice',
    paper: 'toast', organizer: '校园市集活动组',
    openToAllMajors: true,
    deadline_date: '2026-12-20',
    eligibility: '在校学生均可报名，能完成至少一个服务时段。',
    description: '协助校园市集完成摊位签到、物料整理与路线引导。',
  },
];

// The module reads demo records here. Replace the data source when FastAPI is ready.
export const opportunities = sampleOpportunities.map((item) => ({ ...item, source: 'demo', status: 'open' }));

export function categoryLabel(category) {
  return categories.find(([id]) => id === category)?.[1] ?? '机会';
}

export function matchesOpportunity(item, category, major) {
  if (category !== 'all' && item.category !== category) return false;
  if (major === 'all') return true;
  if (major === 'open') return item.openToAllMajors === true;
  return item.openToAllMajors || item.majors?.includes(major) === true;
}

export function safeOfficialUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}

export function recognitionFor(item) {
  if (item.category !== 'competition') return null;
  const recognition = item.recognition;
  if (!['A', 'B'].includes(recognition?.level)) return null;
  if (item.source === 'demo') return recognition;
  return recognition.school && recognition.edition && safeOfficialUrl(recognition.source_url) ? recognition : null;
}

const dateFormat = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric',
});
const shortDateFormat = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', month: 'long', day: 'numeric',
});
const timeFormat = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

export function deadlineLabel(item, showTime = false) {
  const raw = item.deadline_at ?? (item.deadline_date && item.deadline_date + 'T00:00:00+08:00');
  const date = new Date(raw ?? Number.NaN);
  if (!Number.isFinite(date.getTime())) return null;
  const day = (showTime ? dateFormat : shortDateFormat).format(date);
  return showTime && item.deadline_at ? day + ' ' + timeFormat.format(date) : day;
}

export function opportunityStatus(item, now = Date.now()) {
  if (item.status === 'closed') return '已截止';
  const cutoff = item.deadline_at
    ? Date.parse(item.deadline_at)
    : item.deadline_date && Date.parse(item.deadline_date + 'T00:00:00+08:00') + 86_400_000;
  if (!Number.isFinite(cutoff)) return '待核实';
  if (now >= cutoff) return '已截止';
  if (item.status === 'upcoming') return '即将开放';
  if (item.status === 'open') return item.category === 'research' ? '招募中' : '报名中';
  return '待核实';
}

export function suitableMajors(item) {
  if (item.openToAllMajors) return '不限专业';
  const names = majors.filter(([id]) => item.majors?.includes(id)).map(([, name]) => name);
  return names.length ? names.join('、') : '待核实';
}
