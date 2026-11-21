import React, { useState } from 'react';
import { ArrowLeft, ChevronDown } from 'lucide-react';
import cat from '../../assets/opportunities/cat.webp';
import cloud from '../../assets/opportunities/cloud.webp';
import postcard from '../../assets/opportunities/postcard.webp';
import leaf from '../../assets/opportunities/leaf.webp';
import ticket from '../../assets/opportunities/ticket.webp';
import toast from '../../assets/opportunities/toast.webp';
import trophy from '../../assets/opportunities/trophy.webp';
import flask from '../../assets/opportunities/flask.webp';
import envelope from '../../assets/opportunities/envelope.webp';
import { categories, categoryLabel, deadlineLabel, majors, matchesOpportunity, opportunities, opportunityStatus, recognitionFor } from './opportunityData.js';
import { OpportunityDetails } from './OpportunityDetails.jsx';
import './opportunities.css';

const papers = { cat, cloud, postcard, leaf, ticket, toast };
const stickers = { trophy, flask, envelope };

function OpportunityNote({ item, onOpen }) {
  const { title, category, paper, sticker } = item;
  const deadline = deadlineLabel(item);
  const recognition = recognitionFor(item);
  const status = opportunityStatus(item);

  return (
    <li className="opportunity-note" data-paper={paper}>
      <button className="opportunity-note__button" type="button" aria-haspopup="dialog" onClick={() => onOpen(item)}>
        <img className="opportunity-note__paper" src={papers[paper] ?? papers.cat} alt="" draggable={false} />
        <span className="opportunity-note__body">
          <strong>{title}</strong>
          <span className="opportunity-note__meta">{categoryLabel(category)} · {deadline ? `${deadline}截止` : '截止待核实'}</span>
          {category === 'competition' && (
            <span className="opportunity-note__grade">
              {recognition ? `${recognition.level} 类${item.source === 'demo' ? '（示例）' : ''}` : '等级待核实'}
            </span>
          )}
          {['已截止', '即将开放', '待核实'].includes(status) && <span className="opportunity-note__status">{status}</span>}
        </span>
        {stickers[sticker] && <img className="opportunity-note__sticker" src={stickers[sticker]} alt="" draggable={false} />}
      </button>
    </li>
  );
}

export function OpportunityBoard({ titleRef }) {
  const [category, setCategory] = useState('all');
  const [major, setMajor] = useState('all');
  const [selected, setSelected] = useState(null);
  const visible = opportunities.filter((item) => matchesOpportunity(item, category, major));
  const hasDemo = opportunities.some(({ source }) => source === 'demo');

  function resetFilters() {
    setCategory('all');
    setMajor('all');
  }

  return (
    <main className="opportunities" aria-labelledby="opportunities-title">
      <section className="opportunities__board">
        <header className="opportunities__header">
          <div className="opportunities__topline">
            <a className="opportunities__return" href="#/notebook"><ArrowLeft size={17} aria-hidden="true" /> 返回目录</a>
            {hasDemo && <span className="opportunities__sample">示例数据</span>}
          </div>
          <h1 id="opportunities-title" ref={titleRef} tabIndex={-1}>冒险公告栏</h1>
          <div className="opportunities__filters">
            <div className="opportunities__categories" role="group" aria-label="机会分类">
              {categories.map(([id, label]) => (
                <button key={id} type="button" aria-pressed={category === id} onClick={() => setCategory(id)}>{label}</button>
              ))}
            </div>
            <label className="opportunities__major">
              <span>专业筛选</span>
              <span className="opportunities__select">
                <select value={major} onChange={(event) => setMajor(event.target.value)} aria-label="专业筛选">
                  <option value="all">全部专业</option>
                  <option value="open">只看不限专业</option>
                  {majors.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
                <ChevronDown size={16} aria-hidden="true" />
              </span>
            </label>
          </div>
        </header>
        <p className="opportunities-sr-only" role="status">找到 {visible.length} 条机会</p>
        {visible.length ? (
          <ul className="opportunities__notes">
            {visible.map((item) => <OpportunityNote key={item.id} item={item} onOpen={setSelected} />)}
          </ul>
        ) : (
          <section className="opportunities__empty">
            <h2>没有符合筛选条件的机会</h2>
            <button type="button" onClick={resetFilters}>清除筛选</button>
          </section>
        )}
      </section>
      {selected && <OpportunityDetails opportunity={selected} stickers={stickers} onClose={() => setSelected(null)} />}
    </main>
  );
}
