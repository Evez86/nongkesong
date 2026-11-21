import { readCampusPlan } from '../trainingPlan/trainingPlanData.js';

export const campusSchool = '中国农业大学';
export const campusPortal = 'https://one.cau.edu.cn/tp_up/';

function campusBase(value) {
  const base = value?.trim();
  if (base === '/') return '';
  try {
    const url = new URL(base);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) return null;
    return url.href.replace(/\/+$/, '');
  } catch {
    return null;
  }
}

const apiBase = campusBase(import.meta.env?.VITE_CAMPUS_API_BASE_URL);
const campusPath = `${apiBase ?? ''}/api/v1/campus`;

export const hasCampusIntegration = apiBase !== null;
export const campusLoginUrl = `${campusPath}/login`;

async function request(path, { method = 'GET', signal } = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener('abort', cancel, { once: true });
  if (signal?.aborted) cancel();
  const timeout = setTimeout(cancel, 15_000);
  try {
    const response = await fetch(`${campusPath}/${path}`, {
      method, signal: controller.signal, credentials: 'include', cache: 'no-store', redirect: 'error',
    });
    if (!response.ok) {
      const error = new Error('校园服务暂时不可用，请稍后重试。');
      error.status = response.status;
      throw error;
    }
    return method === 'GET' ? await response.json() : null;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', cancel);
  }
}

export async function fetchCampusSession(signal) {
  try {
    const data = await request('session', { signal });
    if (data?.authenticated === false) return null;
    if (data?.authenticated !== true) throw new Error('校园登录状态暂时无法确认。');
    return { name: typeof data.display_name === 'string' ? data.display_name.trim() : '' };
  } catch (error) {
    if (error.status === 401) return null;
    throw error;
  }
}

function readTimetable(data) {
  if (!Array.isArray(data?.weekdays) || !data.weekdays.length ||
    !data.weekdays.every((day) => typeof day === 'string' && day.trim()) ||
    !Number.isInteger(data.period_count) || data.period_count < 1 ||
    !Array.isArray(data.meetings)) return null;

  const meetings = data.meetings.flatMap((meeting) => {
    if (!Number.isInteger(meeting?.day) || meeting.day < 0 || meeting.day >= data.weekdays.length ||
      !Number.isInteger(meeting.start) || meeting.start < 1 ||
      !Number.isInteger(meeting.end) || meeting.end < meeting.start || meeting.end > data.period_count ||
      typeof meeting.title !== 'string' || !meeting.title.trim()) return [];
    return [{
      day: meeting.day, start: meeting.start, end: meeting.end, title: meeting.title,
      room: typeof meeting.room === 'string' ? meeting.room : '',
      tone: ['oak', 'birch', 'clay', 'honey'].includes(meeting.tone) ? meeting.tone : 'oak',
    }];
  });

  return {
    weekdays: data.weekdays,
    periodCount: data.period_count,
    eveningStart: Number.isInteger(data.evening_start) && data.evening_start > 0
      ? data.evening_start : data.period_count + 1,
    meetings,
    termLabel: typeof data.term_label === 'string' ? data.term_label : '',
  };
}

export async function fetchCampusAcademicData(signal) {
  const data = await request('academic-data', { signal });
  return { plan: readCampusPlan(data?.training_plan), timetable: readTimetable(data?.timetable) };
}

export async function endCampusSession(signal) {
  try {
    await request('logout', { method: 'POST', signal });
  } catch (error) {
    if (error.status !== 401) throw error;
  }
}
