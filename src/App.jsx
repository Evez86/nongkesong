import React, { useLayoutEffect, useRef, useSyncExternalStore } from 'react';
import { EntranceScene } from './components/EntranceScene.jsx';
import { NotebookDesk } from './components/NotebookDesk.jsx';
import { CourseBook } from './features/courses/CourseBook.jsx';
import { GrowthRoadmap } from './features/roadmap/GrowthRoadmap.jsx';
import { DailyDiary } from './features/diary/DailyDiary.jsx';
import { OpportunityBoard } from './features/opportunities/OpportunityBoard.jsx';
import { LibraryPage } from './features/library/LibraryPage.jsx';
import { useCampusConnection } from './features/campus/useCampusConnection.js';
import { sections } from './sections.js';

function subscribeToPageChange(listener) {
  window.addEventListener('hashchange', listener);
  return () => window.removeEventListener('hashchange', listener);
}

function readPage() {
  const hash = window.location.hash;
  if (hash === '#/notebook') return 'notebook';
  return sections.find(({ href }) => href === hash)?.id ?? 'home';
}

export default function App() {
  const page = useSyncExternalStore(subscribeToPageChange, readPage);
  const campus = useCampusConnection();
  const bookLink = useRef(null);
  const pageTitle = useRef(null);
  const previousPage = useRef(page);

  useLayoutEffect(() => {
    const from = previousPage.current;
    if (from === page) return;

    previousPage.current = page;
    window.scrollTo(0, 0);
    let target = page === 'home' ? bookLink.current : pageTitle.current;
    if (page === 'notebook') {
      target = document.getElementById(`directory-${from}`) ?? target;
    }
    target?.focus({ preventScroll: true });
  }, [page]);

  if (page === 'courses') return <CourseBook titleRef={pageTitle} campus={campus} />;
  if (page === 'roadmap') return <GrowthRoadmap titleRef={pageTitle} />;
  if (page === 'daily') return <DailyDiary titleRef={pageTitle} />;
  if (page === 'opportunities') return <OpportunityBoard titleRef={pageTitle} />;
  if (page === 'library') return <LibraryPage titleRef={pageTitle} />;
  if (page === 'notebook') return <NotebookDesk titleRef={pageTitle} />;
  return <EntranceScene bookLinkRef={bookLink} campus={campus} />;
}
