const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const listeners = new Map(), canvasListeners = new Map();
let pauses = 0, closed = 0;
const audio = {readyState: 0, duration: NaN, currentTime: 0, src: '/audio.mp3',
  pause() {pauses++;},
  addEventListener(name, callback) {listeners.set(name, callback);},
  removeEventListener(name) {listeners.delete(name);}};
const canvas = {width: 800, height: 80, getContext() {return {clearRect() {}, fillRect() {}};},
  getBoundingClientRect() {return {left: 0, width: 800};},
  addEventListener(name, callback) {canvasListeners.set(name, callback);},
  removeEventListener(name) {canvasListeners.delete(name);}};
const status = {};
const sandbox = {AbortController, setTimeout, clearTimeout,
  fetch: async () => ({ok: true, headers: {get() {return null;}}, arrayBuffer: async () => new ArrayBuffer(4)}),
  AudioContext: class {
    async decodeAudioData() {return {duration: 10, getChannelData() {return new Float32Array(16000);}};}
    async close() {closed++;}
  }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('static/annotation_audio_calibration.js', 'utf8'), sandbox);
(async () => {
  const cleanup = sandbox.AnnotationAudioCalibration.attach({audio, canvas, status, initialTime: 4.258,
    markers: [{start: 4.326, end: 4.946}]});
  audio.readyState = 1; audio.duration = 10;
  listeners.get('loadedmetadata')();
  assert.equal(audio.currentTime, 4.258, 'saved position must survive metadata loading');
  canvasListeners.get('click')({clientX: 400});
  assert.equal(audio.currentTime, 5);
  assert.equal(pauses, 1, 'waveform seek must pause playback');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(closed, 1, 'decoded audio context must close');
  cleanup();
  assert.equal(listeners.size, 0, 'page changes must detach old audio callbacks');
  assert.equal(canvasListeners.size, 0);
  console.log('audio calibration position and lifecycle checks passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
