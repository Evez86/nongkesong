import React, { useLayoutEffect, useRef, useState } from 'react';
import desk from '../assets/notebook-desk.webp';
import { DirectoryPage } from './DirectoryPage.jsx';
import { Sticker } from './Sticker.jsx';
import { sections } from '../sections.js';

export function NotebookDesk({ titleRef }) {
  const [selection, setSelection] = useState(null);
  const sectionTitle = useRef(null);
  const lastEntry = useRef(null);
  const activeSection = sections.find(({ id }) => id === selection);

  useLayoutEffect(() => {
    if (activeSection) {
      sectionTitle.current?.focus({ preventScroll: true });
    } else if (lastEntry.current) {
      document.getElementById(lastEntry.current)?.focus({ preventScroll: true });
      lastEntry.current = null;
    }
  }, [activeSection]);

  function openSection(id) {
    lastEntry.current = `directory-${id}`;
    setSelection(id);
  }

  return (
    <main className="desk">
      <a className="desk-return" href="#">回到首页</a>
      <div className="desk-stage">
        <div className="desk-art">
          <img className="desk-picture" src={desk} width="1536" height="1024"
            fetchPriority="high" alt="暖灯下，咖啡杯和睡着的橘猫围着一本平摊的手帐" />
          <div className="sleeping-cat" aria-hidden="true">
            <img className="desk-picture" src={desk} width="1536" height="1024" alt="" />
          </div>
          <div className="coffee-steam" aria-hidden="true"><i /><i /><i /></div>
        </div>

        <header className="notebook-title">
          <h1 ref={titleRef} tabIndex={-1}>松果来信</h1>
          <p lang="en">Pine Letters</p>
        </header>

        {activeSection ? (
          <section className="notebook-page section-intro" aria-labelledby="page-title" key={activeSection.id}>
            <button className="return-button" onClick={() => setSelection(null)}>返回目录</button>
            <Sticker region={activeSection.sticker} />
            <h2 id="page-title" ref={sectionTitle} tabIndex={-1}>{activeSection.title}</h2>
            <p>{activeSection.description}。</p>
            <p className="preview-note">该模块将在后续阶段开放。</p>
          </section>
        ) : <DirectoryPage onOpen={openSection} />}
      </div>
    </main>
  );
}
