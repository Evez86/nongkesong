function storageKey(stageId) {
  return `pine-letters.roadmap-note.v1.${stageId}`;
}

export function getStageNote(stage) {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(stage.id)));
    if (saved && typeof saved.title === 'string' && saved.title.trim() &&
      typeof saved.description === 'string' && Array.isArray(saved.actions) &&
      saved.actions.every((action) => action && typeof action.text === 'string' && typeof action.done === 'boolean')) {
      return saved;
    }
  } catch {
    // Unavailable storage or an invalid entry falls back to the editable example.
  }

  return {
    title: stage.title,
    description: stage.description,
    actions: stage.actions.map((text) => ({ text, done: false })),
  };
}

export function saveStageNote(stageId, note) {
  localStorage.setItem(storageKey(stageId), JSON.stringify(note));
}
