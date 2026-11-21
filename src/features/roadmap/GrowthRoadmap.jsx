import React, { useRef, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import parchment from '../../assets/roadmap-parchment.webp';
import landmarks from '../../assets/roadmap-landmarks.webp';
import destinations from '../../assets/roadmap-destinations.webp';
import { Sticker } from '../../components/Sticker.jsx';
import { MapRoute } from './MapRoute.jsx';
import { StageNote } from './StageNote.jsx';
import { getStageNote, saveStageNote } from './roadmapNotes.js';
import { INITIAL_STAGE, MAP_HEIGHT, MAP_WIDTH, stages } from './roadmapStages.js';
import './growthRoadmap.css';

export function GrowthRoadmap({ titleRef }) {
  const [selectedId, setSelectedId] = useState(INITIAL_STAGE);
  const [notes, setNotes] = useState(() => Object.fromEntries(stages.map((stage) => [stage.id, getStageNote(stage)])));
  const noteRef = useRef(null);
  const selectedStage = stages.find(({ id }) => id === selectedId);

  function changeNote(note) {
    setNotes((previous) => ({ ...previous, [selectedId]: note }));
    try {
      saveStageNote(selectedId, note);
      return true;
    } catch {
      return false;
    }
  }

  function selectStage(id) {
    setSelectedId(id);
    if (window.matchMedia('(max-width: 900px), (max-height: 590px)').matches) {
      noteRef.current?.scrollIntoView({ block: 'nearest' });
    }
  }

  return (
    <main className="growth-roadmap" aria-labelledby="growth-roadmap-title">
      <div className="roadmap-frame">
        <a className="roadmap-return" href="#/notebook"><ArrowLeft size={17} aria-hidden="true" /> 返回目录</a>
        <header className="roadmap-heading">
          <h1 id="growth-roadmap-title" ref={titleRef} tabIndex={-1}>成长路线图</h1>
          <p>大学四年 · 八个学期</p>
        </header>
        <span className="roadmap-sample">演示路线</span>
        <p className="roadmap-swipe">左右滑动地图，点地标查看学期目标。</p>

        <section className="roadmap-viewport" aria-label="四年八学期探险地图">
          <div className="roadmap-scene">
            <img className="roadmap-parchment" src={parchment} width="1536" height="1024" alt="" />
            <MapRoute />
            <ol className="roadmap-stops">
              {stages.map((stage) => {
                const [,, width, height] = stage.sticker;
                return (
                  <li className={`roadmap-stop${stage.labelAbove ? ' roadmap-stop--above' : ''}`} key={stage.id}
                    style={{
                      '--stop-x': `${stage.x / MAP_WIDTH * 100}%`,
                      '--stop-y': `${stage.y / MAP_HEIGHT * 100}%`,
                      '--sticker-w': `${stage.size * width / Math.max(width, height) / MAP_WIDTH * 100}cqw`,
                      '--sticker-h': `${stage.size * height / Math.max(width, height) / MAP_WIDTH * 100}cqw`,
                      '--sticker-angle': `${stage.angle}deg`,
                    }}>
                    <button type="button" aria-current={stage.id === selectedId ? 'step' : undefined}
                      aria-controls="growth-note" onClick={() => selectStage(stage.id)}>
                      <Sticker region={stage.sticker} source={stage.destination ? destinations : landmarks}
                        className="roadmap-sticker" />
                      <span className="roadmap-stop__label"><strong>{stage.term}</strong><span>{stage.shortTitle}</span></span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </section>
        <StageNote key={selectedStage.id} term={selectedStage.term} note={notes[selectedId]} onChange={changeNote} noteRef={noteRef} />
      </div>
    </main>
  );
}
