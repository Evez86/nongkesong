import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Sticker } from '../../components/Sticker.jsx';
import { sections } from '../../sections.js';
import decorations from '../../assets/coursebook-stickers.webp';
import { creditCategories, selectedTerm, semesters, timetable } from './courseBookSample.js';
import { WeekTimetable } from './WeekTimetable.jsx';
import { TrainingPlanCourses, TrainingPlanSummary } from '../trainingPlan/TrainingPlanResult.jsx';
import './courseBook.css';

const courseSection = sections.find(({ id }) => id === 'courses');
const earned = creditCategories.reduce((total, category) => total + category.earned, 0);
const required = creditCategories.reduce((total, category) => total + category.required, 0);
const remaining = required - earned;

function DemoCredits() {
  return (
    <>
      <section className="course-credit-note" aria-labelledby="credit-heading">
        <h2 id="credit-heading">毕业学分</h2>
        <div className="course-credit-note__numbers">
          <p className="course-credit-note__total"><strong>{earned}</strong> / {required} <small>学分</small></p>
          <p className="course-credit-note__remaining">还需 <strong>{remaining}</strong> 学分</p>
        </div>
        <div className="course-credit-note__progress" role="progressbar" aria-label="毕业学分进度"
          aria-valuemin={0} aria-valuenow={earned} aria-valuemax={required} aria-valuetext={`已修 ${earned} / ${required} 学分`}>
          <span style={{ width: `${earned / required * 100}%` }} />
        </div>
      </section>

      <table className="course-credits" aria-label="各类毕业学分">
        <thead><tr><th scope="col">学分类别</th><th scope="col">已修 / 要求</th><th scope="col">待修</th></tr></thead>
        <tbody>
          {creditCategories.map(({ name, earned, required }) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>{earned} / {required}</td>
              <td>{required - earned} 学分</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="course-book__note">已修学分按成绩记录，毕业要求按培养方案。</p>
      <a className="course-book__campus-link" href="#">回首页连接校园平台</a>
    </>
  );
}

function DemoSchedule() {
  return (
    <>
      <ul className="course-semesters" aria-label="八个学期">
        {semesters.map((term, index) => (
          <li key={term} aria-current={index === selectedTerm ? 'true' : undefined}
            data-term={index <= selectedTerm ? 'past' : 'future'}>{term}</li>
        ))}
      </ul>

      <div className="course-schedule__meta">
        <h3>{semesters[selectedTerm]} · 本学期</h3><p>计划修读 {timetable.termCredits} 学分</p>
      </div>
      <WeekTimetable {...timetable} />
      <p className="course-book__note">校园平台课表示例 · 节次数与晚课时段按学校安排</p>
    </>
  );
}

export function CourseBook({ titleRef, campus }) {
  const [view, setView] = useState('plan');
  const { phase, dataPhase, academic, refresh } = campus;
  const connected = phase === 'connected' || phase === 'loggingOut';
  const checking = phase === 'checking';
  const showSample = !connected && !checking;
  const plan = academic?.plan;
  const campusTimetable = academic?.timetable;
  const showPlan = Boolean(plan && (view === 'plan' || !campusTimetable));
  const canSwitch = Boolean(plan && campusTimetable);
  return (
    <main className="paper-spread course-book" aria-labelledby="course-book-title">
      <section className="paper-spread__page paper-spread__page--left course-paper course-paper--credits" aria-labelledby="course-book-title">
        <a className="course-book__return" href="#/notebook"><ArrowLeft size={17} aria-hidden="true" /> 返回目录</a>
        <header className="course-book__title-row">
          <Sticker region={courseSection.sticker} className="course-book__title-sticker" />
          <h1 id="course-book-title" ref={titleRef} tabIndex={-1}>{courseSection.title}</h1>
          {showSample && <span className="course-book__sample">示例数据</span>}
          {connected && <span className="course-book__sample">校园数据</span>}
        </header>

        {showSample && <DemoCredits />}
        {plan && <TrainingPlanSummary plan={plan} />}
        {connected && dataPhase === 'ready' && !plan && (
          <p className="course-book__campus-note">当前没有可同步的培养方案。</p>
        )}
        <Sticker region={[88, 288, 394, 439]} source={decorations} className="course-decoration course-decoration--coffee" />
      </section>

      <section className="paper-spread__page paper-spread__page--right course-paper course-paper--schedule" aria-labelledby="course-schedule-heading">
        <Sticker region={[1064, 306, 395, 424]} source={decorations} className="course-decoration course-decoration--pinecone" />
        <header className="course-schedule__header">
          <h2 id="course-schedule-heading">{showPlan ? '培养方案' : '学期安排'}</h2>
          {canSwitch && (
            <div className="course-schedule__views course-schedule__views--active" role="group" aria-label="学期视图">
              <button type="button" aria-pressed={view === 'plan'} onClick={() => setView('plan')}>课程清单</button>
              <button type="button" aria-pressed={view === 'schedule'} onClick={() => setView('schedule')}>校园周课表</button>
            </div>
          )}
          {showSample && <div className="course-schedule__views"><span aria-current="true">示例周课表</span></div>}
        </header>

        {showSample && <DemoSchedule />}
        {showPlan && <TrainingPlanCourses key={plan.plan_id} plan={plan} />}
        {!showPlan && campusTimetable && (
          <>
            {campusTimetable.termLabel && <h3 className="course-book__campus-note">{campusTimetable.termLabel}</h3>}
            <WeekTimetable {...campusTimetable} />
          </>
        )}
        {(checking || dataPhase === 'loading') && <p role="status">正在获取校园数据…</p>}
        {connected && dataPhase === 'ready' && !plan && !campusTimetable && <p>当前没有可同步的课表。</p>}
        {connected && dataPhase === 'denied' && <p role="alert">当前会话尚未获得课表和培养方案的数据权限。</p>}
        {connected && dataPhase === 'error' && (
          <div>
            <p role="alert">暂时无法读取校园数据。</p>
            <button type="button" className="course-book__campus-link" onClick={refresh}>重新同步</button>
          </div>
        )}
        <Sticker region={[516, 335, 491, 395]} source={decorations} className="course-decoration course-decoration--cat" />
      </section>
    </main>
  );
}
