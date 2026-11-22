import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import parchment from '../../assets/roadmap-parchment.webp';
import landmarks from '../../assets/roadmap-landmarks.webp';
import destinations from '../../assets/roadmap-destinations.webp';
import { Sticker } from '../../components/Sticker.jsx';
import { CampusSyncStatus } from '../campus/CampusSyncStatus.jsx';
import { MapRoute } from './MapRoute.jsx';
import { RoadmapPlanner } from './RoadmapPlanner.jsx';
import { StageNote } from './StageNote.jsx';
import { getStageNote, saveStageNote } from './roadmapNotes.js';
import { INITIAL_STAGE, MAP_HEIGHT, MAP_WIDTH, stages } from './roadmapStages.js';
import './growthRoadmap.css';

export function GrowthRoadmap({ titleRef, campus, usingVisitorData, roadmap, onRoadmapChange }) {
  const { academic, phase, dataPhase, refresh } = campus;
  const campusTerm = academic?.profile.currentTerm;
  const [selectedId, setSelectedId] = useState(() => stages[(campusTerm ?? roadmap?.profile.term) - 1]?.id ?? INITIAL_STAGE);
  const [notes, setNotes] = useState(() => Object.fromEntries(stages.map((stage) => [stage.id, getStageNote(stage)])));
  const noteRef = useRef(null);
  const selectedStage = stages.find(({ id }) => id === selectedId);
  const selectedIndex = stages.indexOf(selectedStage);
  const selectedNote = roadmap ? roadmap.notes[selectedIndex] : usingVisitorData ? notes[selectedId] : null;
  const demoStudent = campus.session?.demo || academic?.source === 'demo';

  useEffect(() => {
    if (campusTerm) setSelectedId(stages[campusTerm - 1].id);
  }, [campusTerm]);

  function changeNote(note) {
    if (roadmap) {
      onRoadmapChange((previous) => ({
        ...previous, notes: previous.notes.map((item, index) => index === selectedIndex ? note : item),
      }));
      return true;
    }
    setNotes((previous) => ({ ...previous, [selectedId]: note }));
    try {
      saveStageNote(selectedId, note);
      return true;
    } catch {
      return false;
    }
  }

  function openGeneratedRoadmap(nextRoadmap) {
    onRoadmapChange(nextRoadmap);
    selectStage(stages[nextRoadmap.profile.term - 1]?.id ?? selectedId);
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
        <div className="roadmap-controls">
          {usingVisitorData && (
            <>
              <span className="roadmap-sample" role="status">{roadmap ? '按自填资料生成 · 规则版' : '演示路线'}</span>
              <RoadmapPlanner profile={roadmap?.profile} onGenerate={openGeneratedRoadmap} />
            </>
          )}
          {phase === 'connected' && <span className="roadmap-sample" role="status">{demoStudent ? '校园联调 · 测试资料' : roadmap ? '校园资料 · 规则版' : '校园资料'}</span>}
          {academic?.plan && <RoadmapPlanner profile={roadmap?.profile} academic={academic}
            onGenerate={openGeneratedRoadmap} onSessionExpired={refresh} />}
        </div>
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
        {selectedNote ? <StageNote key={`${roadmap?.id ?? 'sample'}-${selectedId}`} term={selectedStage.term} note={selectedNote}
          onChange={changeNote} noteRef={noteRef} temporary={Boolean(roadmap)} /> : (
          <aside className="roadmap-note roadmap-note--campus" ref={noteRef} aria-label="校园成长路线状态">
            <div className="roadmap-note__body">
              <h2>我的校园路线</h2>
              {academic?.profile.major && <p>{academic.profile.major}{campusTerm && ` · ${stages[campusTerm - 1].term}`}</p>}
              <CampusSyncStatus campus={campus} />
              {academic?.plan && <p>点击「生成校园路线」，在当前学期查看目标。</p>}
              {academic && !academic.plan && <p>培养方案同步后可生成校园路线。</p>}
              {(phase === 'error' || (phase === 'connected' && dataPhase !== 'loading' && !academic?.plan)) && (
                <button className="roadmap-plan-button" type="button" onClick={refresh}>重新同步</button>
              )}
              {academic && <a className="roadmap-campus-link" href="#/notebook/courses">查看学期课程簿</a>}
            </div>
          </aside>
        )}
      </div>
    </main>
  );
}
