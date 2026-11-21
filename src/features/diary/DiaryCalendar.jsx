import React from 'react';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { Sticker } from '../../components/Sticker.jsx';
import moodSheet from '../../assets/diary-mood-stickers.webp';
import { formatDay, getWeeks, moods, offsetMonth } from './diaryData.js';

const weekdays = ['一', '二', '三', '四', '五', '六', '日'];

export function DiaryCalendar({ month, setMonth, selected, today, entries, deadlines, onPick, onAddDeadline }) {
  const [year, monthNumber] = month.split('-');

  return (
    <section className="diary-calendar" aria-labelledby="diary-calendar-heading">
      <header className="diary-row">
        <h2 id="diary-calendar-heading">日历</h2>
        <button className="diary-primary" type="button" onClick={onAddDeadline}>
          <Plus size={16} aria-hidden="true" /> 设置 DDL
        </button>
      </header>
      <div className="diary-calendar__nav">
        <span>{year} 年 {Number(monthNumber)} 月</span>
        <div className="diary-actions">
          <button aria-label="上个月" type="button" onClick={() => setMonth(offsetMonth(month, -1))}><ChevronLeft size={17} /></button>
          <button aria-label="下个月" type="button" onClick={() => setMonth(offsetMonth(month, 1))}><ChevronRight size={17} /></button>
        </div>
      </div>

      <table aria-label={`${year} 年 ${Number(monthNumber)} 月日历`}>
        <thead><tr>{weekdays.map((day) => <th scope="col" key={day}>{day}</th>)}</tr></thead>
        <tbody>
          {getWeeks(month).map((week, index) => (
            <tr key={index}>
              {week.map((date, weekday) => {
                if (!date) return <td className="diary-calendar__blank" key={weekday} />;
                const mood = moods.find(({ id }) => id === entries[date]?.mood);
                const dayDeadlines = deadlines.filter((deadline) => deadline.date === date);
                const mainDeadline = dayDeadlines.find(({ done }) => !done) ?? dayDeadlines[0];
                const parts = [formatDay(date), date === today ? '今天' : '', mood?.name,
                  ...dayDeadlines.map(({ title }) => `截止事项：${title}`)].filter(Boolean);

                return (
                  <td key={date}>
                    <button className="diary-calendar__day" type="button" onClick={() => onPick(date)}
                      aria-current={date === selected ? 'date' : undefined} aria-label={parts.join('，')}
                      data-today={date === today || undefined}>
                      <span className="diary-calendar__number">{Number(date.slice(-2))}</span>
                      {mood && <Sticker source={moodSheet} region={mood.sticker} className="diary-calendar__sticker" />}
                      {mainDeadline && <span className="diary-calendar__ddl" data-done={mainDeadline.done || undefined}>
                        <span>{mainDeadline.title}</span>{dayDeadlines.length > 1 && <small>+{dayDeadlines.length - 1}</small>}
                      </span>}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
