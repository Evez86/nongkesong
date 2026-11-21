import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Bell } from 'lucide-react';
import { Sticker } from '../../components/Sticker.jsx';
import { sections } from '../../sections.js';
import { DiaryCalendar } from './DiaryCalendar.jsx';
import { DiaryDay } from './DiaryDay.jsx';
import { DiaryEditor } from './DiaryEditor.jsx';
import { MoodRecord } from './MoodRecord.jsx';
import { deadlineTimes, DIARY_STORAGE_KEY, formatDay, initialDiary, readDiary, todayKey, toggleTask } from './diaryData.js';
import './dailyDiary.css';

const daily = sections.find(({ id }) => id === 'daily');
const emptyMood = { mood: '', text: '' };

export function DailyDiary({ titleRef }) {
  const [now, setNow] = useState(Date.now);
  const today = todayKey(new Date(now));
  const [selected, setSelected] = useState(today);
  const [month, setMonth] = useState(today.slice(0, 7));
  const [diary, setDiary] = useState(() => initialDiary(today));
  const [drafts, setDrafts] = useState({});
  const [editor, setEditor] = useState(null);
  const [saveError, setSaveError] = useState('');
  const [moodMessage, setMoodMessage] = useState('');
  const currentDiary = useRef(diary);
  const dayContent = useRef(null);
  const record = drafts[selected] ?? diary.moods[selected] ?? emptyMood;
  const tasks = diary.tasks.filter((task) => task.date === selected);
  const deadlines = diary.deadlines.filter((item) => item.date === selected).sort((a, b) => a.time.localeCompare(b.time));
  const reminders = diary.deadlines.filter((item) => {
    const { remindAt } = deadlineTimes(item);
    return !item.done && remindAt !== null && now >= remindAt;
  });
  const hasSample = [...diary.tasks, ...diary.deadlines, ...diary.awards, ...Object.values(diary.moods)]
    .some((item) => item.sample);

  useEffect(() => {
    const refreshClock = () => setNow(Date.now());
    const interval = window.setInterval(refreshClock, 15_000);
    window.addEventListener('focus', refreshClock);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', refreshClock);
    };
  }, []);

  useEffect(() => {
    function sync(event) {
      if (event.key !== DIARY_STORAGE_KEY) return;
      const saved = readDiary();
      if (!saved) return;
      currentDiary.current = saved;
      setDiary(saved);
    }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  function update(transform) {
    const next = transform(currentDiary.current);
    currentDiary.current = next;
    setDiary(next);
    try {
      localStorage.setItem(DIARY_STORAGE_KEY, JSON.stringify(next));
      setSaveError('');
      return true;
    } catch {
      setSaveError('浏览器暂时无法保存。改动仍显示在当前页面。');
      return false;
    }
  }

  function pickDate(date, reveal = false) {
    setSelected(date);
    setMonth(date.slice(0, 7));
    setMoodMessage('');
    if (reveal && window.matchMedia('(max-width: 760px)').matches) {
      dayContent.current?.scrollIntoView({ block: 'start' });
    }
  }

  function edit(type, item) {
    setEditor({ type, item, date: selected });
  }

  function saveItem(fields) {
    const { type, item, date } = editor;
    const key = type === 'task' ? 'tasks' : 'deadlines';
    const entry = {
      id: item?.id ?? crypto.randomUUID(), date, done: item?.done ?? false,
      ...fields,
    };
    update((data) => ({
      ...data,
      [key]: item ? data[key].map((previous) => previous.id === item.id ? entry : previous) : [...data[key], entry],
    }));
    if (type === 'deadline') pickDate(entry.date);
  }

  function removeItem(type, item) {
    if (!window.confirm(`删除「${item.title}」？`)) return;
    const key = type === 'task' ? 'tasks' : 'deadlines';
    update((data) => ({ ...data, [key]: data[key].filter(({ id }) => id !== item.id) }));
  }

  function saveMood() {
    const text = record.text.trim();
    const saved = update((data) => {
      const entries = { ...data.moods };
      if (record.mood || text) entries[selected] = { mood: record.mood, text };
      else delete entries[selected];
      return { ...data, moods: entries };
    });
    setDrafts((previous) => {
      const next = { ...previous };
      delete next[selected];
      return next;
    });
    setMoodMessage(saved ? '心情记录已保存。' : '');
  }

  return (
    <main className="paper-spread daily-diary" aria-labelledby="diary-heading">
      <section className="paper-spread__page paper-spread__page--left diary-page">
        <a className="diary-return" href="#/notebook"><ArrowLeft size={17} aria-hidden="true" /> 返回目录</a>
        <header className="diary-title">
          <Sticker region={daily.sticker} className="diary-title__sticker" />
          <h1 id="diary-heading" ref={titleRef} tabIndex={-1}>{daily.title}</h1>
          {hasSample && <span className="diary-sample">含示例数据</span>}
        </header>

        <div className="diary-day" ref={dayContent}>
          <p className="diary-date" aria-live="polite">{formatDay(selected)} <span>{selected === today ? '今天' : '已选日期'}</span></p>
          <DiaryDay date={selected} tasks={tasks} deadlines={deadlines} awards={diary.awards} now={now}
            onEdit={edit} onDelete={removeItem} onToggleTask={(id) => update((data) => toggleTask(data, id))}
            onToggleDeadline={(id) => update((data) => ({
              ...data, deadlines: data.deadlines.map((item) => item.id === id ? { ...item, done: !item.done } : item),
            }))} />
        </div>
        {saveError && <p className="diary-storage-error" role="alert">{saveError}</p>}
      </section>

      <section className="paper-spread__page paper-spread__page--right diary-page diary-page--calendar">
        <MoodRecord date={selected} record={record} onSave={saveMood} message={moodMessage}
          onDraft={(value) => { setDrafts((previous) => ({ ...previous, [selected]: value })); setMoodMessage(''); }} />
        {reminders.length > 0 && (
          <div className="diary-reminders" role="status">
            <p><Bell size={16} aria-hidden="true" /> DDL 提醒</p>
            <ul>{reminders.map((item) => (
              <li key={item.id}><button type="button" onClick={() => pickDate(item.date, true)}>
                {item.title} · {formatDay(item.date)} {item.time} 截止
              </button></li>
            ))}</ul>
          </div>
        )}
        <DiaryCalendar month={month} setMonth={setMonth} selected={selected} today={today}
          entries={diary.moods} deadlines={diary.deadlines} onPick={(date) => pickDate(date, true)}
          onAddDeadline={() => edit('deadline')} />
      </section>

      {editor && <DiaryEditor editor={editor} onSave={saveItem} onClose={() => setEditor(null)} />}
    </main>
  );
}
