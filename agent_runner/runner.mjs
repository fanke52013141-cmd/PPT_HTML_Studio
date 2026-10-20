// Full Pi SDK harness. Host owns files, validation, budget and result authority.
import readline from 'node:readline';
import { createAgentSession, createExtensionRuntime, ModelRuntime, SessionManager, SettingsManager } from '@earendil-works/pi-coding-agent';
import { InMemoryCredentialStore } from '@earendil-works/pi-ai';

const lines = readline.createInterface({ input: process.stdin });
const send = value => process.stdout.write(`${JSON.stringify(value)}\n`);
let startResolve;
const started = new Promise(resolve => { startResolve = resolve; });
const pending = new Map(); let serial = 0;
lines.on('line', line => {
  const value = JSON.parse(line);
  if (value.type === 'start') startResolve(value);
  else if (value.type === 'tool_result') { pending.get(value.id)?.(value); pending.delete(value.id); }
});
lines.on('close', () => process.exit(1));
async function call(name, args) {
  const id = ++serial;
  const response = new Promise(resolve => pending.set(id, resolve));
  send({ type: 'tool', id, name, args });
  const result = await response;
  return { content: result.content, details: {}, isError: !!result.error, terminate: !!result.terminate };
}
let session;
try {
  const input = await started;
  const glmThinking = input.model.model.toLowerCase().startsWith('glm-5.3') && input.model.thinking === 'enabled';
  const runtime = await ModelRuntime.create({ credentials: new InMemoryCredentialStore(), modelsPath: null,
    modelsStorePath: `${process.cwd()}/models-cache.json`, refreshOnCreate: false, allowModelNetwork: false });
  runtime.registerProvider('studio', { baseUrl: input.model.endpoint, apiKey: input.model.api_key,
    api: 'openai-completions', authHeader: true, models: [{ id: input.model.model, name: input.model.model,
      reasoning: false, input: ['text', 'image'], contextWindow: 128000, maxTokens: input.model.max_tokens,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      compat: { supportsDeveloperRole: false, supportsStore: false, supportsUsageInStreaming: true } }] });
  const stream = runtime.streamSimple.bind(runtime); let calls = 0;
  runtime.streamSimple = (model, context, options) => {
    if (++calls > input.limits.max_model_calls) {
      send({ type: 'error', code: 'budget_exceeded' });
      throw Error('budget_exceeded');
    }
    send({ type: 'model_call', count: calls });
    return stream(model, context, { ...options, maxTokens: input.model.max_tokens,
      ...(glmThinking ? { onPayload: async (payload, target) => {
        const changed = await options?.onPayload?.(payload, target);
        const body = { ...(changed ?? payload), thinking: { type: 'enabled' },
          max_tokens: input.model.max_tokens, temperature: input.model.temperature ?? 1.0 };
        delete body.max_completion_tokens;
        delete body.reasoning_effort;
        return body;
      } } : {}),
      ...(input.model.temperature == null ? {} : { temperature: input.model.temperature }) });
  };
  const object = properties => ({ type: 'object', properties, required: Object.keys(properties), additionalProperties: false });
  const string = { type: 'string' };
  const definitions = input.mode === 'json' ? [
    ['submit_json', 'Return the complete JSON object required by the supplied schema. No approval or file writes.', object({ result: { type: 'object' } })],
  ] : [
    ['read_material', 'Read one exact text member from the sealed task bundle. Start with ENTRY.md, decision-input.json, constraints.json and task.json.', object({ name: string })],
    ['view_image', 'View actual baseline bundle image or candidate image ID returned by check_candidate; do not invent observations.', object({ name: string })],
    ['check_candidate', 'Run official preflight and original DOM/animation checks. Counts as one candidate round. Failed check returns real feedback. Return complete replacement operations based on baseline.', object({ result: { type: 'object' } })],
    ['submit_result', 'Submit last checked result plus actual before/after visual observations. For missing capability/no legal solution submit unsupported/needs_input with no operations. No author save.', object({ result: { type: 'object' }, baseline_notes: string, candidate_notes: string })],
  ];
  const tools = definitions.map(([name, description, parameters]) => ({ name, label: name, description, parameters,
    execute: async (_id, args) => call(name, args) }));
  const resourceLoader = {
    getExtensions: () => ({ extensions: [], errors: [], runtime: createExtensionRuntime() }),
    getSkills: () => ({ skills: [], diagnostics: [] }), getPrompts: () => ({ prompts: [], diagnostics: [] }),
    getThemes: () => ({ themes: [], diagnostics: [] }), getAgentsFiles: () => ({ agentsFiles: [] }),
    getSystemPrompt: () => input.system, getSystemPromptSource: () => undefined,
    getAppendSystemPrompt: () => [], getAppendSystemPromptSources: () => [], extendResources: () => {}, reload: async () => {},
  };
  ({ session } = await createAgentSession({ cwd: process.cwd(), agentDir: process.cwd(), modelRuntime: runtime,
    model: runtime.getModel('studio', input.model.model), tools: tools.map(t => t.name), customTools: tools,
    thinkingLevel: 'off', resourceLoader, sessionManager: SessionManager.inMemory(process.cwd()),
    settingsManager: SettingsManager.inMemory({ compaction: { enabled: false }, cacheWarming: 'off',
      retry: { enabled: false, provider: { maxRetries: 0, timeoutMs: input.limits.timeout_seconds * 1000 } } }) }));
  session.subscribe(event => {
    if (event.type === 'message_end' && event.message?.role === 'assistant') {
      send({ type: 'turn', stop_reason: event.message.stopReason,
        tokens: event.message.usage?.totalTokens ?? null });
    }
  });
  await session.prompt(input.prompt, input.images?.length ? { images: input.images } : undefined);
  send({ type: 'done' });
} catch (error) {
  send({ type: 'error', code: error.message === 'budget_exceeded' ? 'budget_exceeded' : 'provider_error' });
} finally {
  session?.dispose(); lines.close();
}
