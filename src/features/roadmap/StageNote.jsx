import React, { useLayoutEffect, useRef, useState } from 'react';
import { Pencil } from 'lucide-react';

export function StageNote({ term, note, onChange, noteRef }) {
  const dialogRef = useRef(null);
  const editButton = useRef(null);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState('');

  useLayoutEffect(() => {
    if (editing && !dialogRef.current.open) dialogRef.current.showModal();
  }, [editing]);

  function closeEditor() {
    setEditing(false);
    editButton.current?.focus({ preventScroll: true });
  }

  function updateNote(nextNote, announce = false) {
    const saved = onChange(nextNote);
    setMessage(saved ? (announce ? '便签已保存。' : '') : '浏览器无法永久保存，本次改动在当前页面有效。');
  }

  function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const title = data.get('title').trim();

    if (!title) {
      form.elements.title.setCustomValidity('请输入目标标题。');
      form.elements.title.reportValidity();
      return;
    }

    const previous = note.actions.slice();
    const actions = data.get('actions').split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((text) => {
      const index = previous.findIndex((action) => action.text === text);
      const done = index === -1 ? false : previous.splice(index, 1)[0].done;
      return { text, done };
    });

    updateNote({ title, description: data.get('description').trim(), actions }, true);
    dialogRef.current.close();
  }

  return (
    <aside className="roadmap-note" id="growth-note" ref={noteRef} aria-labelledby="growth-objective">
      <div className="roadmap-note__header">
        <p>{term} · 学期目标</p>
        <button className="roadmap-note__edit" ref={editButton} type="button" onClick={() => setEditing(true)}>
          <Pencil size={14} aria-hidden="true" /> 编辑便签
        </button>
      </div>
      <div className="roadmap-note__body">
        <h2 id="growth-objective">{note.title}</h2>
        {note.description && <p className="roadmap-note__intro">{note.description}</p>}
        {note.actions.length > 0 && (
          <ul className="roadmap-actions" aria-label="行动清单">
            {note.actions.map((action, index) => (
              <li key={index}>
                <label>
                  <input type="checkbox" checked={action.done} onChange={(event) => {
                    const done = event.target.checked;
                    const actions = note.actions.map((item, position) => position === index ? { ...item, done } : item);
                    updateNote({ ...note, actions });
                  }} />
                  <span>{action.text}</span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="roadmap-note__status" role="status">{message}</p>

      <dialog className="roadmap-editor" ref={dialogRef} onClose={closeEditor} aria-labelledby="growth-edit-title">
        {editing && (
          <form onSubmit={submit}>
            <h2 id="growth-edit-title">编辑{term}便签</h2>
            <label>
              目标标题
              <input name="title" defaultValue={note.title} required autoFocus
                onInput={(event) => event.target.setCustomValidity('')} />
            </label>
            <label>说明<textarea name="description" rows={3} defaultValue={note.description} /></label>
            <label>
              行动清单
              <span className="roadmap-editor__hint">每行写一条。删掉一行即可移除这项行动。</span>
              <textarea name="actions" rows={5} defaultValue={note.actions.map(({ text }) => text).join('\n')} />
            </label>
            <div className="roadmap-editor__buttons">
              <button type="button" onClick={() => dialogRef.current.close()}>取消</button>
              <button type="submit">保存便签</button>
            </div>
          </form>
        )}
      </dialog>
    </aside>
  );
}
