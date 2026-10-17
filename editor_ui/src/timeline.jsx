import React, { createRef } from 'react';
import { createRoot } from 'react-dom/client';
import { Timeline } from '@xzdarcy/react-timeline-editor';
import '@xzdarcy/react-timeline-editor/dist/react-timeline-editor.css';

// No effects, play() or tick subscriptions: only edit UI and externally set cursor.
export function mountTimeline(host, { rows, onEdit, onSeek, onSelect, onGestureStart = () => {} }) {
  const root = createRoot(host), ref = createRef();
  let disposed = false;
  function render(nextRows) {
    if (disposed) return;
    root.render(<Timeline ref={ref} editorData={structuredClone(nextRows)} effects={{}}
      autoReRender={false} autoScroll={false} enableRowDrag={false}
      scale={1} scaleWidth={80} minScaleCount={20} maxScaleCount={120}
      style={{ width: '100%', height: 220 }}
      onChange={() => false}
      onActionMoveStart={() => { onGestureStart(); }} onActionResizeStart={() => { onGestureStart(); }}
      onActionMoveEnd={event => onEdit({ ...event, resize: false })}
      onActionResizeEnd={event => onEdit({ ...event, resize: true })}
      onClickAction={(_, { action }) => onSelect?.(action.id)}
      onCursorDrag={seconds => onSeek(Math.round(seconds * 1000))}
      onClickTimeArea={seconds => { onSeek(Math.round(seconds * 1000)); return false; }}
      getActionRender={action => <span data-timeline-action={action.id} title={action.description || action.id}>{action.label || action.id}</span>} />);
  }
  render(rows);
  return { update: render, setTime(ms) { if (!disposed) ref.current?.setTime(ms / 1000); },
    destroy() { disposed = true; ref.current?.pause(); root.unmount(); } };
}
