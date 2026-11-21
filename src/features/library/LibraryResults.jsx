import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import courseArt from '../../assets/library/course.webp';
import teacherArt from '../../assets/library/teacher.webp';
import experienceArt from '../../assets/library/experience.webp';
import examArt from '../../assets/library/exam.webp';
import { accessLabel, answerLabel, examTitle } from './libraryData.js';

const resultStyles = {
  course: { label: '课程介绍', action: '课程概览', art: courseArt },
  teacher: { label: '开课教师', action: '查看教师信息', art: teacherArt },
  experience: { label: '学长学姐经验', action: '阅读经验', art: experienceArt },
  exam: { label: '历年真题', action: '查看资料', art: examArt },
};

function makeResult(course, kind, record = course) {
  const result = { ...resultStyles[kind], kind, course, record };
  if (kind === 'course') return { ...result, title: course.name, summary: course.summary };
  if (kind === 'teacher') return {
    ...result, title: `${record.name} · ${record.className}`, summary: `${record.term} · ${record.department}`,
  };
  if (kind === 'experience') return { ...result, title: record.title, summary: record.summary };

  const unavailable = record.availability === 'unavailable';
  return {
    ...result,
    title: examTitle(record),
    summary: unavailable ? '暂无可访问链接' : [record.format && `试卷 ${record.format}`, answerLabel(record)].filter(Boolean).join(' · '),
    access: unavailable ? '' : [record.provider, accessLabel(record.access)].filter(Boolean).join(' · '),
    unavailable,
  };
}

function ResultCard({ result, onOpen, showCategory = true }) {
  const { art, title, summary, label, kind, access, unavailable, action } = result;
  return (
    <li className={`library-result library-result--${kind}`}>
      <div className="library-result__art"><img src={art} alt="" /></div>
      <div className="library-result__copy">
        {showCategory && <span className="library-result__label">{label}</span>}
        <h3>{title}</h3>
        <p>{summary}</p>
        {access && <p className="library-result__access">{access}</p>}
      </div>
      {unavailable ? <span className="library-result__unavailable">入口待补充</span>
        : <button type="button" className="library-action" aria-haspopup="dialog" onClick={() => onOpen(result)}>{action}</button>}
    </li>
  );
}

function Filter({ label, allLabel, value, values, onChange }) {
  return (
    <span className="library-filter">
      <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="all">{allLabel}</option>
        {values.map((entry) => <option key={entry}>{entry}</option>)}
      </select>
      <ChevronDown size={16} aria-hidden="true" />
    </span>
  );
}

function overviewFor(course) {
  const items = [
    makeResult(course, 'course'),
    ...course.teachers.slice(0, 1).map((teacher) => makeResult(course, 'teacher', teacher)),
    ...course.experiences.slice(0, 1).map((experience) => makeResult(course, 'experience', experience)),
  ];
  const firstExam = course.exams[0];
  if (firstExam) items.push({ ...makeResult(course, 'exam', firstExam), title: `${course.name} · ${firstExam.type}真题` });
  return items;
}

const categoryTitles = {
  all: '搜索结果',
  course: '课程介绍',
  teacher: '开课教师',
  experience: '学习经验',
  exam: '历年真题',
};

export function LibraryResults({ courses, category, onOpen }) {
  const [year, setYear] = useState('all');
  const [examType, setExamType] = useState('all');
  const [term, setTerm] = useState('all');
  const exams = courses.flatMap((course) => course.exams);
  const years = [...new Set(exams.map((exam) => exam.year))].sort().reverse();
  const types = [...new Set(exams.map((exam) => exam.type))];
  const terms = [...new Set(courses.flatMap((course) => course.teachers.map((teacher) => teacher.term)))].sort().reverse();
  const isArchive = category === 'exam' || category === 'teacher';

  function resultsFor(course) {
    if (category === 'all') return overviewFor(course);
    if (category === 'course') return [makeResult(course, 'course')];
    if (category === 'teacher') return course.teachers
      .filter((teacher) => term === 'all' || teacher.term === term)
      .map((teacher) => makeResult(course, 'teacher', teacher));
    if (category === 'experience') return course.experiences.map((experience) => makeResult(course, 'experience', experience));
    return course.exams
      .filter((exam) => (year === 'all' || exam.year === year) && (examType === 'all' || exam.type === examType))
      .map((exam) => makeResult(course, 'exam', exam));
  }

  function resetFilters() {
    setYear('all');
    setExamType('all');
    setTerm('all');
  }

  const groups = courses.map((course) => ({ course, results: resultsFor(course) }));
  const count = groups.reduce((sum, { results }) => sum + results.length, 0);
  const filtered = category === 'exam' && (year !== 'all' || examType !== 'all') ||
    category === 'teacher' && term !== 'all';

  return (
    <section className={isArchive ? 'library-results library-results--archive' : 'library-results'} aria-labelledby="library-results-title">
      <header className={isArchive ? 'library-results__header' : 'library-sr-only'}>
        <h2 id="library-results-title">{courses.length === 1 && isArchive ? `${courses[0].name} · ` : ''}{categoryTitles[category]}</h2>
        {category === 'exam' && years.length > 0 && (
          <div className="library-results__filters">
            <Filter label="学年" allLabel="全部学年" value={year} values={years} onChange={setYear} />
            <Filter label="考试类型" allLabel="全部考试类型" value={examType} values={types} onChange={setExamType} />
          </div>
        )}
        {category === 'teacher' && terms.length > 0 && (
          <Filter label="开课学期" allLabel="全部学期" value={term} values={terms} onChange={setTerm} />
        )}
      </header>
      <p className="library-sr-only" role="status">找到 {count} 条结果</p>
      {count === 0 && (
        <div className="library-empty">
          <p>{filtered ? '没有符合筛选条件的资料。' : `暂未收录该课程的${categoryTitles[category]}。`}</p>
          {filtered && <button type="button" className="library-action" onClick={resetFilters}>清除筛选</button>}
        </div>
      )}
      {groups.filter(({ results }) => results.length > 0).map(({ course, results }) => (
        <div className="library-results__group" key={course.id}>
          {groups.length > 1 && <h2 className="library-results__course">{course.name}</h2>}
          <ul className="library-results__list">
            {results.map((result) => (
              <ResultCard key={`${result.kind}:${result.record.id}`} result={result} onOpen={onOpen} showCategory={!isArchive} />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
