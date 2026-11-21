export const DIARY_STORAGE_KEY = 'pine-letters.diary.v1';

export const moods = [
  { id: 'happy', name: '开心', sticker: [74, 69, 397, 411] },
  { id: 'calm', name: '平静', sticker: [558, 119, 402, 360] },
  { id: 'hopeful', name: '期待', sticker: [1051, 82, 424, 398] },
  { id: 'tired', name: '疲惫', sticker: [57, 535, 434, 414] },
  { id: 'sad', name: '难过', sticker: [548, 593, 413, 356] },
  { id: 'irritated', name: '烦躁', sticker: [1035, 566, 469, 383] },
];

export const coffees = [
  { id: 'americano', name: '美式咖啡', sticker: [105, 84, 390, 402] },
  { id: 'oat', name: '燕麦拿铁', sticker: [541, 132, 451, 359] },
  { id: 'caramel', name: '焦糖拿铁', sticker: [1095, 79, 334, 413] },
  { id: 'mocha', name: '摩卡', sticker: [285, 520, 433, 422] },
  { id: 'cinnamon', name: '肉桂拿铁', sticker: [761, 534, 489, 402] },
];

export const deadlineKinds = ['作业', '考试', '报名', '其他'];
export const reminderOptions = [
  ['day-before', '提前 1 天'],
  ['same-day', '当天 09:00'],
  ['none', '不提醒'],
];

const dateFormatter = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
});
const chineseDate = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'UTC', month: 'long', day: 'numeric', weekday: 'long',
});

export function todayKey(now = new Date()) {
  return dateFormatter.format(now);
}

export function formatDay(key) {
  return chineseDate.format(new Date(key + 'T00:00:00Z'));
}

export function offsetDay(key, days) {
  const date = new Date(key + 'T00:00:00Z');
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function offsetMonth(month, offset) {
  const [year, number] = month.split('-').map(Number);
  return new Date(Date.UTC(year, number - 1 + offset, 1)).toISOString().slice(0, 7);
}

export function getWeeks(month) {
  const [year, number] = month.split('-').map(Number);
  const first = new Date(Date.UTC(year, number - 1, 1));
  const firstCell = (first.getUTCDay() + 6) % 7;
  const days = new Date(Date.UTC(year, number, 0)).getUTCDate();
  return Array.from({ length: Math.ceil((firstCell + days) / 7) }, (_, week) =>
    Array.from({ length: 7 }, (_, weekday) => {
      const day = week * 7 + weekday - firstCell + 1;
      return day >= 1 && day <= days ? `${month}-${String(day).padStart(2, '0')}` : null;
    }));
}

function demoDiary(today) {
  const yesterday = offsetDay(today, -1);
  const older = offsetDay(today, -2);
  const tasks = [
    ...['整理专业英语笔记', '读一篇科研实践资料', '完成数据分析练习', '查看本周课程安排', '复盘昨天的错题'].map((title, index) => ({
      id: `sample-today-${index}`, title, date: today, done: index >= 2, sample: true,
    })),
    ...['提交专业英语作业', '完成数据分析练习', '查看下周课程安排', '复盘昨天的错题'].map((title, index) => ({
      id: `sample-yesterday-${index}`, title, date: yesterday, done: true, sample: true,
    })),
    { id: 'sample-older', title: '整理课堂笔记', date: older, done: true, sample: true },
  ];

  return {
    version: 1,
    tasks,
    moods: {
      [today]: { mood: 'calm', text: '做完练习就出门走了一圈，回来时感觉平静了很多。', sample: true },
      [yesterday]: { mood: 'happy', text: '总算交了英语作业。和同学去买了杯咖啡，今天挺开心的。', sample: true },
      [older]: { mood: 'tired', text: '', sample: true },
      [offsetDay(today, -4)]: { mood: 'hopeful', text: '', sample: true },
      [offsetDay(today, -7)]: { mood: 'sad', text: '', sample: true },
      [offsetDay(today, -9)]: { mood: 'irritated', text: '', sample: true },
    },
    deadlines: [
      { id: 'sample-english', title: '英语作业', date: yesterday, time: '22:00', kind: '作业', reminder: 'day-before', done: true, sample: true },
      { id: 'sample-report', title: '科研报告提交', date: offsetDay(today, 4), time: '22:00', kind: '作业', reminder: 'day-before', done: false, sample: true },
      { id: 'sample-register', title: '竞赛报名', date: offsetDay(today, 7), time: '18:00', kind: '报名', reminder: 'same-day', done: false, sample: true },
    ],
    awards: [
      { date: older, coffee: 'americano', sample: true },
      { date: yesterday, coffee: 'oat', sample: true },
    ],
  };
}

function isDateKey(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value + 'T00:00:00Z'));
}

export function readDiary() {
  try {
    const data = JSON.parse(localStorage.getItem(DIARY_STORAGE_KEY));
    if (data?.version !== 1 || !Array.isArray(data.tasks) || !Array.isArray(data.deadlines) ||
      !Array.isArray(data.awards) || !data.moods || typeof data.moods !== 'object' || Array.isArray(data.moods)) return null;

    if (![...data.tasks, ...data.deadlines].every((item) =>
      item && typeof item.id === 'string' && typeof item.title === 'string' && isDateKey(item.date) &&
      typeof item.done === 'boolean')) return null;
    if (!data.deadlines.every((item) => /^\d{2}:\d{2}$/.test(item.time) &&
      deadlineKinds.includes(item.kind) && reminderOptions.some(([id]) => id === item.reminder))) return null;
    if (!data.awards.every((item) => item && isDateKey(item.date) && coffees.some(({ id }) => id === item.coffee))) return null;
    if (!Object.entries(data.moods).every(([day, mood]) => isDateKey(day) && mood &&
      typeof mood.text === 'string' && (!mood.mood || moods.some(({ id }) => id === mood.mood)))) return null;
    return data;
  } catch {
    return null;
  }
}

export function initialDiary(today) {
  return readDiary() ?? demoDiary(today);
}

export function nextCoffee(awards) {
  return coffees.find(({ id }) => !awards.some(({ coffee }) => coffee === id));
}

export function toggleTask(data, taskId) {
  const target = data.tasks.find(({ id }) => id === taskId);
  if (!target) return data;

  const tasks = data.tasks.map((task) => task.id === taskId ? { ...task, done: !task.done } : task);
  if (target.done || data.awards.some(({ date }) => date === target.date) ||
    tasks.some(({ date, done }) => date === target.date && !done)) return { ...data, tasks };

  const coffee = nextCoffee(data.awards);
  const awards = coffee ? [...data.awards, { date: target.date, coffee: coffee.id }] : data.awards;
  return { ...data, tasks, awards };
}

export function deadlineTimes(deadline) {
  const due = Date.parse(`${deadline.date}T${deadline.time}:00+08:00`);
  let remindAt = null;
  if (deadline.reminder === 'day-before') remindAt = due - 86_400_000;
  if (deadline.reminder === 'same-day') {
    remindAt = Math.min(due, Date.parse(`${deadline.date}T09:00:00+08:00`));
  }
  return { due, remindAt };
}
