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

async function request(path, { method = 'GET', body, signal } = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener('abort', cancel, { once: true });
  if (signal?.aborted) cancel();
  const timeout = setTimeout(cancel, 15_000);
  try {
    const response = await fetch(`${campusPath}/${path}`, {
      method, signal: controller.signal, credentials: 'include', cache: 'no-store', redirect: 'error',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const error = new Error('校园服务暂时不可用，请稍后重试。');
      error.status = response.status;
      throw error;
    }
    return response.status === 204 || (method === 'POST' && !body) ? null : await response.json();
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
    return { name: cleanText(data.display_name), demo: data.source === 'demo' };
  } catch (error) {
    if (error.status === 401) return null;
    throw error;
  }
}

function cleanText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function readCredits(value) {
  return Number.isFinite(value) && value >= 0 ? value : null;
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
  const plan = readCampusPlan(data?.training_plan);
  const cohort = data?.profile?.cohort;
  const currentTerm = data?.profile?.current_term;
  return {
    source: data?.source === 'demo' ? 'demo' : 'campus',
    profile: {
      major: cleanText(data?.profile?.program_name) || plan?.program_name || '',
      cohort: (Number.isInteger(cohort) ? String(cohort) : cleanText(cohort)) || plan?.cohort || '',
      currentTerm: Number.isInteger(currentTerm) && currentTerm >= 1 && currentTerm <= 8 ? currentTerm : null,
    },
    credits: {
      earned: readCredits(data?.credit_progress?.earned_credits),
      inProgress: readCredits(data?.credit_progress?.in_progress_credits),
    },
    plan,
    timetable: readTimetable(data?.timetable),
  };
}

export function fetchCampusGrowthPlan(interests, signal) {
  return request('growth-plans', { method: 'POST', body: { interests }, signal });
}

export async function endCampusSession(signal) {
  try {
    await request('logout', { method: 'POST', signal });
  } catch (error) {
    if (error.status !== 401) throw error;
  }
}
