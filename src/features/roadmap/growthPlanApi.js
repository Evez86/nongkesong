import { fetchCampusGrowthPlan } from '../campus/campusApi.js';

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBase = configuredBase?.replace(/\/+$/, '');

export const hasGrowthPlanApi = Boolean(configuredBase);

export async function generateGrowthPlan(profile, signal) {
  const response = await fetch(`${apiBase}/api/v1/growth-plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan_id: null, interests: profile.interests, mode: 'demo' }),
    signal,
  });
  if (!response.ok) throw new Error(`Growth plan service returned ${response.status}`);

  const result = await response.json();
  return readGrowthPlan(result, profile);
}

export async function generateCampusGrowthPlan(profile, academic, signal) {
  const result = await fetchCampusGrowthPlan(profile.interests, signal);
  return readGrowthPlan(result, profile, academic);
}

function readGrowthPlan(result, profile, academic) {
  const source = academic?.source ?? 'demo';
  if (result?.source !== source || typeof result.id !== 'string' ||
    (academic && result.plan_id !== academic.plan.plan_id) ||
    !Array.isArray(result.terms) || result.terms.length !== 8 ||
    !result.terms.every((entry, index) => entry?.term === index + 1 && Array.isArray(entry.goals) &&
      entry.goals.every((goal) => typeof goal?.title === 'string' && Array.isArray(goal.actions) &&
        goal.actions.every((action) => typeof action === 'string')))) {
    throw new Error('Invalid growth plan');
  }

  const courses = new Map(academic?.plan.courses.map((course) => [course.id, course.name]));
  const notes = result.terms.map(({ term, goals }) => {
    const [firstGoal, ...otherGoals] = goals;
    const actions = new Set(goals.flatMap((goal) => goal.actions));
    const isCurrent = term === profile.term;
    if (isCurrent && !academic) {
      actions.add(`对照${profile.major}的培养方案，列出本学期要修的课程和学分`);
      if (profile.interests[0]) actions.add(`为「${profile.interests[0]}」选一个本学期能完成的练习`);
    }
    const descriptions = otherGoals.map((goal) => goal.title);
    if (isCurrent && profile.major) descriptions.unshift(`${profile.major} · 当前学期`);

    const sources = new Set();
    if (academic && goals.length) {
      if (academic.plan.version) sources.add(`培养方案 · ${academic.plan.version}`);
      for (const goal of goals) {
        if (typeof goal.basis === 'string' && goal.basis.trim()) sources.add(goal.basis.trim());
        if (!Array.isArray(goal.course_ids)) continue;
        for (const courseId of goal.course_ids) {
          if (courses.has(courseId)) sources.add(`关联课程 · ${courses.get(courseId)}`);
        }
      }
    }

    return {
      title: firstGoal?.title ?? (isCurrent && !academic ? '整理本学期的学习计划' : '本学期暂无规则目标'),
      description: descriptions.join('\n'),
      actions: [...actions].map((text) => ({ text, done: false })),
      sources: [...sources],
    };
  });
  return { id: result.id, profile, notes };
}

