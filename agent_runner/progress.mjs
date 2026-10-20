// Count SDK-visible events only. Never emit reasoning, output or tool arguments.
export function streamProgress(send, now = () => performance.now()) {
  const started = now(); let lastSent = -5000;
  const value = { state: 'waiting', first_event_seconds: null, first_content_seconds: null,
    last_event_seconds: null, content_chars: 0, reasoning_chars: 0, tool_argument_chars: 0 };
  return event => {
    const elapsed = (now() - started) / 1000;
    const hadContent = value.first_content_seconds != null;
    if (event.type === 'message_start' && event.message?.role === 'assistant') {
      value.first_event_seconds ??= elapsed; value.last_event_seconds = elapsed;
    } else if (event.type === 'message_update') {
      const part = event.assistantMessageEvent;
      value.first_event_seconds ??= elapsed; value.last_event_seconds = elapsed;
      const length = typeof part?.delta === 'string' ? part.delta.length : 0;
      if (part?.type === 'thinking_delta') value.reasoning_chars += length;
      if (part?.type === 'text_delta') value.content_chars += length;
      if (part?.type === 'toolcall_delta') value.tool_argument_chars += length;
      if (value.content_chars || value.tool_argument_chars) value.first_content_seconds ??= elapsed;
      value.state = value.first_content_seconds == null ? 'thinking' : 'outputting';
    } else if (event.type !== 'message_end' || event.message?.role !== 'assistant') return;
    if (now() - lastSent >= 5000 || event.type === 'message_end' || (!hadContent && value.first_content_seconds != null)) {
      lastSent = now(); send({ type: 'stream_progress', ...value, elapsed_seconds: elapsed });
    }
  };
}
