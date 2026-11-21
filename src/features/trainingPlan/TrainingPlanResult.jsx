import React, { useState } from 'react';
import { categoryLabel } from './trainingPlanData.js';
import './trainingPlan.css';

function creditText(credits) {
  return credits === null ? '待核实' : `${credits} 学分`;
}

function sourceText({ page, table, row } = {}) {
  return [page && `第 ${page} 页`, table && `表 ${table}`, row && `第 ${row} 行`].filter(Boolean).join(' · ');
}

export function TrainingPlanSummary({ plan }) {
  const { program_name, cohort, credit_summary, parse_status, warnings } = plan;

  return (
    <section className="training-summary" aria-label="培养方案概览">
      <div className="training-summary__labels">
        <span>校园培养方案</span>
        {parse_status === 'partial' && <span>部分字段待核实</span>}
      </div>
      <h3>{program_name || '培养方案'}</h3>
      {cohort && <p className="training-summary__cohort">{cohort} 级</p>}
      <dl>
        <div><dt>方案课程学分</dt><dd>{creditText(credit_summary.parsed_credits)}</dd></div>
        <div><dt>毕业总学分要求</dt><dd>{creditText(credit_summary.graduation_target_credits)}</dd></div>
      </dl>
      {warnings.length > 0 && (
        <ul className="training-summary__warnings">
          {warnings.map(({ message }, index) => <li key={index}>{message}</li>)}
        </ul>
      )}
    </section>
  );
}

export function TrainingPlanCourses({ plan }) {
  const [term, setTerm] = useState('all');
  const terms = [...new Set(plan.courses.map((course) => course.term).filter(Boolean))].sort((a, b) => a - b);
  const showUnknown = plan.courses.some((course) => course.term === null);
  const courses = term === 'all' ? plan.courses : plan.courses.filter((course) => String(course.term) === term);

  return (
    <section className="training-courses" aria-label="培养方案课程清单">
      <div className="training-courses__toolbar">
        <h3>课程清单</h3>
        <label>学期
          <select value={term} onChange={(event) => setTerm(event.target.value)}>
            <option value="all">全部学期</option>
            {terms.map((number) => <option key={number} value={number}>第 {number} 学期</option>)}
            {showUnknown && <option value="null">学期待核实</option>}
          </select>
        </label>
      </div>
      {courses.length ? <ul className="training-courses__list">
        {courses.map(({ id, code, name, term: courseTerm, category, credits, source_ref }, index) => {
          const source = sourceText(source_ref);
          return (
            <li key={`${id}:${index}`}>
              <div>
                <strong>{name}</strong>
                <p>{[code, courseTerm ? `第 ${courseTerm} 学期` : '学期待核实', categoryLabel(category)].filter(Boolean).join(' · ')}</p>
              </div>
              <div className="training-courses__credits">
                <span>{creditText(credits)}</span>
                {source && <small>{source}</small>}
              </div>
            </li>
          );
        })}
      </ul> : <p>该学期没有已识别的课程。</p>}
    </section>
  );
}
