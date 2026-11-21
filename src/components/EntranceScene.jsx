import React, { useState } from 'react';
import readingRoom from '../assets/reading-room-hd.webp';
import { EntranceAtmosphere } from './EntranceAtmosphere.jsx';
import { ReadingPageTurn } from './ReadingPageTurn.jsx';
import { CampusCatButton, CampusDialog } from '../features/campus/CampusEntrance.jsx';

export function EntranceScene({ bookLinkRef, campus }) {
  const [campusOpen, setCampusOpen] = useState(false);
  const openCampus = () => setCampusOpen(true);
  const connected = Boolean(campus.session);
  return (
    <main className="entrance" aria-label="松果来信">
      <div className="entrance-scene">
        <img src={readingRoom} width="1858" height="846" fetchPriority="high"
          alt="雨窗旁，女孩在暖灯下读书，橘猫蜷在书堆上睡觉" />
        <EntranceAtmosphere source={readingRoom} />
        <ReadingPageTurn />
        <a className="entrance-book" href="#/notebook" ref={bookLinkRef}
          aria-label="翻开女孩手里的书" />
        <CampusCatButton onOpen={openCampus} />
      </div>
      <p className="entrance-hint">
        点击书本翻开手帐<span className="campus-hint-separator">·</span>
        <span className="entrance-hint__campus">{connected ? '已连接中农大 · 点击橘猫查看' : '点击橘猫登录校园'}</span>
      </p>
      <CampusCatButton compact connected={connected} scene={readingRoom} onOpen={openCampus} />
      {campusOpen && <CampusDialog campus={campus} onClose={() => setCampusOpen(false)} />}
    </main>
  );
}
