"use strict";
// Render one bound html-visual scene + its confirmed narration audio into a
// single-slide MP4 segment (E01). Shares the preview bundle and the exact
// seek() evaluation path used by the on-screen player and the frame harness:
// no wall-clock animation, no second layout implementation.
// Usage:
//   node tools/export-slide-video.cjs <scene.json> <audio> <out.mp4> [fps]
const fs = require("fs"),
  path = require("path"),
  os = require("os"),
  { spawnSync } = require("child_process");
const { pathToFileURL } = require("url");

const [scenePath, audioPath, outputPath, fpsArg] = process.argv.slice(2);
if (!scenePath || !audioPath || !outputPath) {
  console.error("usage: export-slide-video.cjs <scene.json> <audio> <out.mp4> [fps]");
  process.exit(2);
}
const fps = Number(fpsArg || 30);
if (!Number.isFinite(fps) || fps < 1 || fps > 60) throw new Error("fps out of range");
const root = path.resolve(__dirname, "..");
const projectResources = require("./project-resources.cjs").loadProjectResources();
const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));
const durationMs = Math.round(Number(scene.durationMs));
if (!Number.isFinite(durationMs) || durationMs < 1000)
  throw new Error("scene durationMs invalid");

const frameCount = Math.ceil((durationMs / 1000) * fps);
const audioDuration = Number(ffprobeJson(audioPath).format.duration);
if (!Number.isFinite(audioDuration) || audioDuration <= 0) throw new Error("audio duration invalid");
const outputDuration = Math.max(frameCount / fps, audioDuration);
const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "hps-slide-"));
const framesDir = path.join(workDir, "frames");
fs.mkdirSync(framesDir);
// Every exit path (browser, seek, encode, probe) removes the frame tree.
process.on("exit", () => {
  try {
    fs.rmSync(workDir, { recursive: true, force: true });
  } catch {}
});

function ffmpeg(args) {
  const result = spawnSync(process.env.FFMPEG_BIN || "ffmpeg", args, { encoding: "utf8" });
  if (result.status !== 0)
    throw new Error("ffmpeg failed: " + (result.stderr || "").slice(-800));
}

function ffprobeJson(target) {
  const result = spawnSync(
    process.env.FFPROBE_BIN || "ffprobe",
    ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", target],
    { encoding: "utf8" },
  );
  if (result.status !== 0)
    throw new Error("ffprobe failed: " + (result.stderr || "").slice(-400));
  return JSON.parse(result.stdout);
}

function resolveChromePath(playwright) {
  if (process.env.HPS_CHROME) return process.env.HPS_CHROME;
  const discovered = playwright.chromium.executablePath();
  if (discovered && fs.existsSync(discovered)) return discovered;
  // Validated Chromium on this machine; same fallback as visual/tests/verify.cjs.
  return "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe";
}

(async () => {
  const playwright = require("playwright");
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: resolveChromePath(playwright),
  });
  const errors = [];
  try {
    const page = await browser.newPage({
      viewport: { width: 1600, height: 900 },
      deviceScaleFactor: 1,
    });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 20000 });
    await page.evaluate((r) => { window.__projectResources = r; }, projectResources);
    const applied = await page.evaluate((s) => window.visualPlayer.apply(s, window.__projectResources), scene);
    if (!applied) throw new Error("scene failed to compile/prepare");
    for (let i = 0; i < frameCount; i += 1) {
      const ms = Math.round((i * 1000) / fps);
      const result = await page.evaluate((t) => window.visualPlayer.seek(t), ms);
      if (result.timeMs !== ms) throw new Error(`seek mismatch at frame ${i}`);
      const shot = await page.locator(".visual-stage").screenshot();
      fs.writeFileSync(
        path.join(framesDir, `frame-${String(i).padStart(5, "0")}.png`),
        shot,
      );
    }
    if (errors.length) throw new Error("page errors: " + errors[0]);
  } finally {
    await browser.close();
  }
  // No -shortest: the narration tail must never be truncated; the container
  // duration equals the audio length, the last frame holds visually.
  ffmpeg([
    "-y",
    "-framerate", String(fps),
    "-i", path.join(framesDir, "frame-%05d.png"),
    "-i", audioPath,
    "-vf", `scale=1600:900:out_color_matrix=bt709:out_range=tv,tpad=stop_mode=clone:stop_duration=${Math.max(0,outputDuration-frameCount/fps)},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709`,
    "-af", "apad",
    "-t", String(outputDuration),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
    "-r", String(fps),
    "-c:a", "aac",
    "-b:a", "192k",
    outputPath,
  ]);
  const probe = ffprobeJson(outputPath);
  const video = probe.streams.find((s) => s.codec_type === "video");
  const audio = probe.streams.find((s) => s.codec_type === "audio");
  if (!video || !audio) throw new Error("segment missing video or audio stream");
  if(video.width!==1600||video.height!==900||video.pix_fmt!=="yuv420p") throw new Error("segment visual format invalid");
  if([video.color_space,video.color_transfer,video.color_primaries].some(v=>v!=="bt709")) throw new Error("segment color tags invalid: " + JSON.stringify({space:video.color_space,transfer:video.color_transfer,primaries:video.color_primaries}));
  if(Math.abs(Number(probe.format.duration)-outputDuration)>1/fps+0.05) throw new Error("segment duration mismatch");
  console.log(JSON.stringify({
    format: "hps.visual.slide-video",
    sceneId: scene.id,
    frames: frameCount,
    fps,
    width: video.width,
    height: video.height,
    durationSec: Number(probe.format.duration),
    audioCodec: audio.codec_name,
  }));
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
