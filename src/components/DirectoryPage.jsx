import React from 'react';
import { sections } from '../sections.js';
import { Sticker } from './Sticker.jsx';

export function DirectoryPage({ onOpen }) {
  return (
    <section className="notebook-page directory" aria-labelledby="page-title">
      <h2 id="page-title">手帐目录</h2>

      <ul className="directory-list">
        {sections.map(({ id, title, sticker, href }) => {
          const content = <><Sticker region={sticker} /><span className="entry-title">{title}</span></>;
          const entryId = `directory-${id}`;

          return (
            <li key={id}>
              {href ? (
                <a id={entryId} className="directory-entry" href={href}>{content}</a>
              ) : (
                <button id={entryId} className="directory-entry" onClick={() => onOpen(id)}>{content}</button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
