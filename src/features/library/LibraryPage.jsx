import React, { useState } from 'react';
import { ArrowLeft, Search } from 'lucide-react';
import { Sticker } from '../../components/Sticker.jsx';
import { sections } from '../../sections.js';
import { courses, findCourses, initialCourseQuery, libraryTabs } from './libraryData.js';
import { LibraryDetails } from './LibraryDetails.jsx';
import { LibraryResults } from './LibraryResults.jsx';
import './library.css';

const library = sections.find(({ id }) => id === 'library');

export function LibraryPage({ titleRef }) {
  const [input, setInput] = useState(initialCourseQuery);
  const [query, setQuery] = useState(initialCourseQuery);
  const [category, setCategory] = useState('all');
  const [detail, setDetail] = useState(null);
  const matches = findCourses(query);

  function submit(event) {
    event.preventDefault();
    setQuery(input.trim());
  }

  function pickCourse(name) {
    setInput(name);
    setQuery(name);
    setCategory('all');
  }

  return (
    <main className="library-page" aria-labelledby="library-title">
      <div className="library-topline">
        <a className="library-return" href="#/notebook"><ArrowLeft size={17} aria-hidden="true" /> 返回目录</a>
        {courses.some(({ source }) => source === 'demo') && <span className="library-sample">示例资料</span>}
      </div>
      <header className="library-heading">
        <Sticker region={library.sticker} className="library-heading__sticker" />
        <h1 id="library-title" ref={titleRef} tabIndex={-1}>森林图书馆</h1>
      </header>
      <div className="library-column">
        <form className="library-search" role="search" aria-label="搜索图书馆课程" onSubmit={submit}>
          <label className="library-sr-only" htmlFor="library-query">课程名称</label>
          <input id="library-query" type="search" value={input} placeholder="输入课程名称"
            onChange={(event) => setInput(event.target.value)} />
          <button type="submit"><Search aria-hidden="true" size={24} /> 搜索</button>
        </form>
        <nav className="library-tabs" aria-label="资料分类">
          {libraryTabs.map(([id, label]) => (
            <button key={id} type="button" aria-pressed={category === id} onClick={() => setCategory(id)}>{label}</button>
          ))}
        </nav>
        {matches.length > 0 ? (
          <LibraryResults key={query} courses={matches} category={category} onOpen={setDetail} />
        ) : (
          <section className="library-empty" aria-labelledby="library-empty-title">
            <h2 id="library-empty-title" role="status">{query ? `没有找到「${query}」的课程资料` : '输入课程名开始查找'}</h2>
            <div className="library-empty__choices">
              {courses.map(({ id, name }) => <button key={id} type="button" className="library-action" onClick={() => pickCourse(name)}>{name}</button>)}
            </div>
          </section>
        )}
      </div>
      {detail && <LibraryDetails detail={detail} onClose={() => setDetail(null)} />}
    </main>
  );
}
