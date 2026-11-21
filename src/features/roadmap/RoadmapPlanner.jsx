import React, { useEffect, useRef, useState } from 'react';
import { generateCampusGrowthPlan, generateGrowthPlan, hasGrowthPlanApi } from './growthPlanApi.js';
import { stages } from './roadmapStages.js';

export function RoadmapPlanner({ profile, academic, onGenerate, onSessionExpired }) {
  const dialogRef = useRef(null);
  const pendingRequest = useRef(null);
  const [form, setForm] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const enabled = academic ? Boolean(academic.plan) : hasGrowthPlanApi;

  useEffect(() => () => pendingRequest.current?.abort(), []);

  function open() {
    setForm({ major: profile?.major ?? '', term: profile?.term ?? 1, interests: profile?.interests.join('、') ?? '' });
    setError('');
  }

  useEffect(() => {
    if (form && !dialogRef.current.open) dialogRef.current.showModal();
  }, [form]);

  function close() {
    pendingRequest.current?.abort();
    pendingRequest.current = null;
    setPending(false);
    setForm(null);
  }

  async function submit(event) {
    event.preventDefault();
    if (!enabled || pendingRequest.current) return;

    const fields = new FormData(event.currentTarget);
    const major = academic ? academic.profile.major : fields.get('major').trim();
    const term = academic ? academic.profile.currentTerm : Number(fields.get('term'));
    const interests = [...new Set(fields.get('interests').split(/[、,，\n]/).map((item) => item.trim()).filter(Boolean))];
    if (!academic && !major) {
      setError('请填写专业名称。');
      return;
    }
    if (interests.length > 3 || interests.some((interest) => Array.from(interest).length > 20)) {
      setError('最多填写三个方向，每个方向不超过 20 个字。');
      return;
    }

    const controller = new AbortController();
    pendingRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15_000);
    setPending(true);
    setError('');
    try {
      const nextProfile = { major, term, interests };
      const roadmap = academic
        ? await generateCampusGrowthPlan(nextProfile, academic, controller.signal)
        : await generateGrowthPlan(nextProfile, controller.signal);
      if (!controller.signal.aborted && dialogRef.current?.open) {
        onGenerate(roadmap);
        dialogRef.current.close();
      }
    } catch (error) {
      if (pendingRequest.current !== controller) return;
      if (academic && error.status === 401) {
        dialogRef.current?.close();
        onSessionExpired();
      } else if (academic && error.status === 403) {
        setError('当前账号尚未获得路线规划权限。');
      } else if (academic && error.status === 404) {
        setError('校园路线服务尚未接入或方案已更新。可回课程簿重新同步。');
      } else {
        setError('暂时无法生成路线，请重试。');
      }
    } finally {
      clearTimeout(timeout);
      if (pendingRequest.current === controller) {
        pendingRequest.current = null;
        setPending(false);
      }
    }
  }

  return (
    <>
      <button className="roadmap-plan-button" type="button" onClick={open}>
        {profile ? '调整我的路线' : academic ? '生成校园路线' : '生成我的路线'}
      </button>
      <dialog className="roadmap-editor" ref={dialogRef} onClose={close} aria-labelledby="roadmap-plan-title">
        {form && (
          <form onSubmit={submit}>
            <h2 id="roadmap-plan-title">{academic ? '生成校园路线' : '生成我的路线'}</h2>
            {academic ? (
              <>
                <p className="roadmap-planner__detail">{academic.source === 'demo' ? '使用校园联调测试资料生成规则建议。' : '使用已同步的校园资料生成规则建议。'}</p>
                <dl className="roadmap-student">
                  <div><dt>专业</dt><dd>{academic.profile.major || '暂未同步'}</dd></div>
                  <div><dt>入学年级</dt><dd>{academic.profile.cohort ? `${academic.profile.cohort} 级` : '暂未同步'}</dd></div>
                  <div><dt>当前学期</dt><dd>{stages[academic.profile.currentTerm - 1]?.term || '暂未同步'}</dd></div>
                  <div><dt>培养方案版本</dt><dd>{academic.plan.version || '暂未同步'}</dd></div>
                </dl>
              </>
            ) : (
              <>
                <p className="roadmap-planner__detail">根据自填资料生成规则建议。</p>
                <label>专业<input name="major" defaultValue={form.major} maxLength={60} required autoFocus /></label>
                <label>
                  当前学期
                  <select name="term" defaultValue={form.term}>
                    {stages.map((stage, index) => <option value={index + 1} key={stage.id}>{stage.term}</option>)}
                  </select>
                </label>
              </>
            )}
            <label>
              学习方向或兴趣（选填）
              <input name="interests" defaultValue={form.interests} maxLength={80} placeholder="例如：数据分析、科研实践" autoFocus={Boolean(academic)} />
              <span className="roadmap-editor__hint">最多填三个，用顿号隔开。</span>
            </label>
            {!enabled && <p className="roadmap-planner__detail">当前预览尚未接入规划后端。</p>}
            {profile && <p className="roadmap-planner__detail">重新生成会替换当前路线的便签和勾选记录。</p>}
            {error && <p className="roadmap-planner__detail" role="alert">{error}</p>}
            <div className="roadmap-editor__buttons">
              <button type="button" onClick={() => dialogRef.current.close()}>取消</button>
              <button type="submit" disabled={pending || !enabled}>{pending ? '生成中…' : '生成路线'}</button>
            </div>
          </form>
        )}
      </dialog>
    </>
  );
}
