import React, { useLayoutEffect, useRef } from 'react';
import { Bell } from 'lucide-react';
import { deadlineKinds, reminderOptions } from './diaryData.js';

export function DiaryEditor({ editor, onSave, onClose }) {
  const dialog = useRef(null);
  const isDeadline = editor.type === 'deadline';
  const titleLabel = isDeadline ? '事项' : '任务名称';

  useLayoutEffect(() => {
    dialog.current.showModal();
  }, []);

  function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const title = data.get('title').trim();
    if (!title) {
      form.elements.title.setCustomValidity(`请输入${titleLabel}。`);
      form.elements.title.reportValidity();
      return;
    }

    onSave(isDeadline ? {
      title,
      date: data.get('date'),
      time: data.get('time'),
      kind: data.get('kind'),
      reminder: data.get('reminder'),
    } : { title });
    dialog.current.close();
  }

  return (
    <dialog className="diary-editor" ref={dialog} onClose={onClose} aria-labelledby="diary-editor-heading">
      <form onSubmit={submit}>
        <h2 id="diary-editor-heading">
          {isDeadline ? <><Bell size={20} aria-hidden="true" /> {editor.item ? '编辑 DDL 提醒' : '设置 DDL 提醒'}</>
            : editor.item ? '编辑任务' : '添加任务'}
        </h2>
        <label>{titleLabel}<input name="title" required defaultValue={editor.item?.title} autoFocus
          onInput={(event) => event.target.setCustomValidity('')} /></label>
        {isDeadline && (
          <>
            <div className="diary-editor__columns">
              <label>截止日期<input name="date" type="date" required defaultValue={editor.item?.date ?? editor.date} /></label>
              <label>截止时间<input name="time" type="time" required defaultValue={editor.item?.time ?? '22:00'} /></label>
            </div>
            <div className="diary-editor__columns">
              <div className="diary-editor__field">
                <label htmlFor="diary-ddl-kind">类型</label>
                <select id="diary-ddl-kind" name="kind" defaultValue={editor.item?.kind ?? deadlineKinds[0]}>
                  {deadlineKinds.map((kind) => <option key={kind}>{kind}</option>)}
                </select>
              </div>
              <div className="diary-editor__field">
                <label htmlFor="diary-ddl-reminder">提醒时间</label>
                <select id="diary-ddl-reminder" name="reminder" defaultValue={editor.item?.reminder ?? 'day-before'}>
                  {reminderOptions.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
              </div>
            </div>
          </>
        )}
        <div className="diary-editor__buttons">
          <button type="button" onClick={() => dialog.current.close()}>取消</button>
          <button className="diary-primary" type="submit">{isDeadline ? '保存提醒' : '保存任务'}</button>
        </div>
      </form>
    </dialog>
  );
}
