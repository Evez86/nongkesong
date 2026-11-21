import React from 'react';

export function CampusSyncStatus({ campus }) {
  const { phase, dataPhase, academic, logoutError } = campus;
  if (phase === 'checking') return <p role="status">正在检查校园连接…</p>;
  if (phase === 'loggingOut') return <p role="status">正在退出校园会话…</p>;
  if (logoutError) return <p role="alert">退出未完成。个人资料已收起，可重试退出或重新同步。</p>;
  if (phase === 'error') return <p role="alert">暂时无法确认校园登录状态。</p>;
  if (dataPhase === 'loading') return <p role="status">正在同步校园学业数据…</p>;
  if (dataPhase === 'denied') return <p role="alert">当前账号尚未获得学业数据权限。</p>;
  if (dataPhase === 'error') return <p role="alert">校园学业数据暂时无法同步。</p>;
  if (!academic) return null;

  const { profile, credits, plan, timetable } = academic;
  const missing = [
    (!profile.major || !profile.cohort || !profile.currentTerm) && '学生资料',
    !plan && '培养方案',
    !timetable && '周课表',
    credits.earned === null && '已修学分',
    credits.inProgress === null && '在修学分',
  ].filter(Boolean);
  return <p role="status">{missing.length ? `暂未同步：${missing.join('、')}` : '校园学业数据已同步。'}</p>;
}
