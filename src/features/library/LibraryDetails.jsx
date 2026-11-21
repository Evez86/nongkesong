import React, { useLayoutEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { accessLabel, answerLabel, examTitle, resourceHref } from './libraryData.js';

function DetailsLink({ value, children }) {
  const href = resourceHref(value);
  return href ? <a className="library-action" href={href} target="_blank" rel="noopener noreferrer">{children}</a> : null;
}

function CourseDetails({ course }) {
  return (
    <>
      <p>{course.summary}</p>
      <p><strong>建议先修</strong> {course.prerequisites}</p>
      <h3>课程内容</h3>
      <ul>{course.topics.map((topic) => <li key={topic}>{topic}</li>)}</ul>
      <DetailsLink value={course.official_url}>查看学校课程介绍</DetailsLink>
    </>
  );
}

function TeacherDetails({ teacher, course }) {
  return (
    <>
      <dl className="library-detail__facts">
        <div><dt>所属院系</dt><dd>{teacher.department}</dd></div>
        <div><dt>开课学期</dt><dd>{teacher.term}</dd></div>
        <div><dt>教学班</dt><dd>{teacher.className}</dd></div>
      </dl>
      <div className="library-detail__links">
        <DetailsLink value={teacher.profile_url}>打开学校教师主页</DetailsLink>
        <DetailsLink value={teacher.offering_url}>查看开课公告</DetailsLink>
      </div>
      {!resourceHref(teacher.profile_url) && <p className="library-detail__hint">
        {course.source === 'demo' ? '示例教师主页待接入学校资料。' : '学校公开教师主页待收录。'}
      </p>}
    </>
  );
}

function ExamDetails({ exam, course }) {
  const downloads = (exam.files ?? [])
    .map((file) => ({ ...file, href: resourceHref(file.url) }))
    .filter(({ href }) => href);
  const platformUrl = resourceHref(exam.resource_url);
  return (
    <>
      <dl className="library-detail__facts">
        <div><dt>所属学期</dt><dd>{exam.year} 学年{exam.term}</dd></div>
        <div><dt>考试类型</dt><dd>{exam.type}</dd></div>
        <div><dt>试卷格式</dt><dd>{exam.format ?? '待确认'}</dd></div>
        <div><dt>参考答案</dt><dd>{answerLabel(exam)}</dd></div>
        <div><dt>资料来源</dt><dd>{exam.provider ?? '待核实'}</dd></div>
        {exam.access && <div><dt>访问条件</dt><dd>{accessLabel(exam.access) || exam.access_note || '待核实'}</dd></div>}
      </dl>
      {exam.access_note && accessLabel(exam.access) && <p>{exam.access_note}</p>}
      <div className="library-detail__links">
        {downloads.map(({ href, label, filename }) => (
          <a className="library-action" key={href} href={href} download={filename ?? ''}>{label}</a>
        ))}
        <DetailsLink value={platformUrl}>打开资料平台</DetailsLink>
        <DetailsLink value={exam.official_url}>核对资料来源</DetailsLink>
      </div>
      {!downloads.length && !platformUrl && <p className="library-detail__hint">
        {course.source === 'demo' ? '这是一条示例索引，文件和访问入口待收录。' : '目前暂无可访问的试卷文件或平台链接。'}
      </p>}
    </>
  );
}

export function LibraryDetails({ detail, onClose }) {
  const dialog = useRef(null);
  const { title, kind, record, course, label } = detail;

  useLayoutEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => {
      if (element.open) element.close();
    };
  }, []);

  return (
    <dialog ref={dialog} className="library-detail" onClose={onClose} aria-labelledby="library-detail-title">
      <div className="library-detail__surface">
        <header className="library-detail__header">
          <span className="library-result__label">{label}</span>
          {course.source === 'demo' && <span className="library-detail__demo">示例资料</span>}
          <button type="button" className="library-detail__close" aria-label="关闭详情" autoFocus
            onClick={() => dialog.current.close()}><X size={21} aria-hidden="true" /></button>
        </header>
        <h2 id="library-detail-title">{kind === 'exam' ? examTitle(record) : title}</h2>
        {kind !== 'course' && <p className="library-detail__course">{course.name}</p>}
        <div className="library-detail__body">
          {kind === 'course' && <CourseDetails course={course} />}
          {kind === 'teacher' && <TeacherDetails teacher={record} course={course} />}
          {kind === 'experience' && record.tips.map((tip) => <p key={tip}>{tip}</p>)}
          {kind === 'exam' && <ExamDetails exam={record} course={course} />}
        </div>
      </div>
    </dialog>
  );
}
