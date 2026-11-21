import React from 'react';
import { Bell, Pencil, Plus, Trash2 } from 'lucide-react';
import coffeeSheet from '../../assets/diary-coffee-stickers.webp';
import { Sticker } from '../../components/Sticker.jsx';
import { coffees, deadlineTimes, nextCoffee, reminderOptions } from './diaryData.js';

export function DiaryDay({ date, tasks, awards, deadlines, now, onEdit, onToggleTask, onToggleDeadline, onDelete }) {
  const done = tasks.filter((task) => task.done).length;
  const award = coffees.find(({ id }) => awards.some((item) => item.date === date && item.coffee === id));
  const next = nextCoffee(awards);
  const collected = coffees.filter(({ id }) => awards.some(({ coffee }) => coffee === id)).length;

  return (
    <>
      <section className="diary-todo" aria-labelledby="diary-todo-heading">
        <header className="diary-row">
          <h2 id="diary-todo-heading">当天做了什么</h2>
          <button className="diary-primary" type="button" onClick={() => onEdit('task')}>
            <Plus size={17} aria-hidden="true" /> 添加任务
          </button>
        </header>

        {tasks.length ? (
          <ul className="diary-task-list">
            {tasks.map((task) => (
              <li key={task.id} className="diary-task" data-done={task.done || undefined}>
                <label><input type="checkbox" checked={task.done} onChange={() => onToggleTask(task.id)} /><span>{task.title}</span></label>
                <div className="diary-actions">
                  <button type="button" aria-label={`编辑任务：${task.title}`} onClick={() => onEdit('task', task)}><Pencil size={16} /></button>
                  <button type="button" aria-label={`删除任务：${task.title}`} onClick={() => onDelete('task', task)}><Trash2 size={16} /></button>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className="diary-empty">这天还没有待办。</p>}

        <section className="diary-achievement" aria-labelledby="diary-achievement-heading">
          <header className="diary-row">
            <h3 id="diary-achievement-heading">当天成就</h3>
            <span>已完成 {done} / {tasks.length} 项</span>
          </header>
          <progress max={tasks.length || 1} value={done} aria-label="当天任务进度" />
          {award ? (
            <p><Sticker source={coffeeSheet} region={award.sticker} className="diary-achievement__sticker" />已解锁「{award.name}」</p>
          ) : tasks.length > 0 && done === tasks.length ? <p>当天待办已全部完成。</p> : null}
        </section>
      </section>

      {deadlines.length > 0 && (
        <section className="diary-deadlines" aria-labelledby="diary-deadlines-heading">
          <h3 id="diary-deadlines-heading"><Bell size={16} aria-hidden="true" /> 当天 DDL</h3>
          <ul>
            {deadlines.map((item) => {
              const { due } = deadlineTimes(item);
              const reminder = reminderOptions.find(([id]) => id === item.reminder)[1];
              return (
                <li className="diary-deadline" key={item.id}>
                  <div className="diary-deadline__text">
                    <strong>{item.title}</strong>
                    <span>{item.kind} · {item.time} 截止 · {reminder}</span>
                  </div>
                  <label className="diary-deadline__done">
                    <input type="checkbox" checked={item.done} onChange={() => onToggleDeadline(item.id)} aria-label={`完成 DDL：${item.title}`} />
                    <span data-overdue={!item.done && now >= due || undefined}>{item.done ? '已完成' : now >= due ? '已逾期' : '未完成'}</span>
                  </label>
                  <div className="diary-actions">
                    <button type="button" aria-label={`编辑 DDL：${item.title}`} onClick={() => onEdit('deadline', item)}><Pencil size={15} /></button>
                    <button type="button" aria-label={`删除 DDL：${item.title}`} onClick={() => onDelete('deadline', item)}><Trash2 size={15} /></button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section className="diary-coffee" aria-labelledby="diary-coffee-heading">
        <header className="diary-row">
          <h3 id="diary-coffee-heading">咖啡贴纸收藏</h3><span>已收集 {collected} / {coffees.length}</span>
        </header>
        <ul>
          {coffees.map(({ id, name, sticker }) => {
            const unlocked = awards.some(({ coffee }) => coffee === id);
            return <li key={id} data-unlocked={unlocked || undefined} data-next={next?.id === id || undefined}
              aria-label={`${name}，${unlocked ? '已解锁' : '待解锁'}`}>
              <Sticker source={coffeeSheet} region={sticker} className="diary-coffee__sticker" /><span>{name}</span>
            </li>;
          })}
        </ul>
        <p>{next ? `下一款奖励 · ${next.name}` : '已集齐全部咖啡贴纸。'}</p>
      </section>
    </>
  );
}
