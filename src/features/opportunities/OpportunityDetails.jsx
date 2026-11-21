import React, { useLayoutEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { categoryLabel, deadlineLabel, opportunityStatus, recognitionFor, safeOfficialUrl, suitableMajors } from './opportunityData.js';

export function OpportunityDetails({ opportunity, stickers, onClose }) {
  const dialog = useRef(null);
  const { title, category, organizer, eligibility, description, source, sticker } = opportunity;
  const isDemo = source === 'demo';
  const recognition = recognitionFor(opportunity);
  const recognitionUrl = safeOfficialUrl(recognition?.source_url);
  const officialUrl = safeOfficialUrl(opportunity.official_url);
  const suitable = suitableMajors(opportunity);

  useLayoutEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => {
      if (element.open) element.close();
    };
  }, []);

  return (
    <dialog className="opportunity-detail" ref={dialog} onClose={onClose} aria-labelledby="opportunity-detail-title">
      <div className="opportunity-detail__paper">
        <header className="opportunity-detail__top">
          <span className="opportunity-detail__tag">{categoryLabel(category)}</span>
          {isDemo && <span className="opportunity-detail__demo">示例数据</span>}
          <button className="opportunity-detail__close" type="button" aria-label="关闭详情"
            autoFocus onClick={() => dialog.current.close()}><X size={22} aria-hidden="true" /></button>
        </header>
        <div className="opportunity-detail__heading">
          {stickers[sticker] && <img src={stickers[sticker]} alt="" />}
          <h2 id="opportunity-detail-title">{title}</h2>
        </div>
        <ul className="opportunity-detail__badges">
          {suitable !== '待核实' && <li className="opportunity-detail__fit">{opportunity.openToAllMajors ? '不限专业' : '专业相关'}</li>}
          {category === 'competition' && <li className="opportunity-detail__level">
            {recognition ? `${recognition.level} 类${isDemo ? '（示例）' : ''}` : '等级待核实'}
          </li>}
          <li>{opportunityStatus(opportunity)}</li>
        </ul>
        <dl className="opportunity-detail__facts">
          <div><dt>适合专业</dt><dd>{suitable}</dd></div>
          <div><dt>适用对象</dt><dd>{eligibility ?? '待核实'}</dd></div>
          <div><dt>组织方</dt><dd>{organizer ?? '待核实'}</dd></div>
          <div><dt>报名截止</dt><dd>{deadlineLabel(opportunity, true) ?? '待核实'}</dd></div>
          <div><dt>机会简介</dt><dd>{description}</dd></div>
        </dl>
        {category === 'competition' && (
          <div className="opportunity-detail__source">
            <strong>认定依据</strong>
            <div>
              {recognitionUrl ? (
                <a href={recognitionUrl} target="_blank" rel="noopener noreferrer">{recognition.title ?? '查看学校竞赛认定目录'}</a>
              ) : <span>{recognition?.title ?? '学校认定目录待核实'}</span>}
              {recognition && <small>{[recognition.school, recognition.edition].filter(Boolean).join(' · ')}</small>}
            </div>
          </div>
        )}
        <footer className="opportunity-detail__actions">
          <button type="button" onClick={() => dialog.current.close()}>返回公告栏</button>
          {officialUrl ? (
            <a className="opportunity-detail__official" href={officialUrl} target="_blank" rel="noopener noreferrer">
              查看官方公告 <span className="opportunities-sr-only">（在新标签页打开）</span>
            </a>
          ) : (
            <button type="button" className="opportunity-detail__official" disabled>查看官方公告</button>
          )}
          {!officialUrl && <p>{isDemo ? '示例活动暂无官方公告链接' : '官方公告链接待核实'}</p>}
        </footer>
      </div>
    </dialog>
  );
}
