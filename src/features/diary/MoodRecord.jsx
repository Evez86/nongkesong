import React from 'react';
import { Sticker } from '../../components/Sticker.jsx';
import moodSheet from '../../assets/diary-mood-stickers.webp';
import { formatDay, moods } from './diaryData.js';

export function MoodRecord({ date, record, onDraft, onSave, message }) {
  return (
    <section className="diary-mood" aria-labelledby="diary-mood-heading">
      <header className="diary-row">
        <h2 id="diary-mood-heading">心情记录</h2><span>{formatDay(date)}</span>
      </header>
      <div className="diary-mood__choices" role="group" aria-label="选择心情">
        {moods.map(({ id, name, sticker }) => (
          <button key={id} type="button" aria-pressed={record.mood === id}
            onClick={() => onDraft({ ...record, mood: record.mood === id ? '' : id })}>
            <Sticker source={moodSheet} region={sticker} className="diary-mood__sticker" />
            <span>{name}</span>
          </button>
        ))}
      </div>
      <form className="diary-mood__entry" onSubmit={(event) => { event.preventDefault(); onSave(); }}>
        <label htmlFor="diary-mood-text">给这一天留一句话</label>
        <textarea id="diary-mood-text" rows={2} value={record.text}
          onChange={(event) => onDraft({ ...record, text: event.target.value })} />
        <div className="diary-row">
          <span className="diary-mood__status" role="status">{message}</span>
          <button className="diary-primary" type="submit">保存记录</button>
        </div>
      </form>
    </section>
  );
}
