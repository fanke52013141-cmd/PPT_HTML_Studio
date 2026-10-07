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
const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));
const durationMs = Math.round(Number(scene.durationMs));
if (!Number.isFinite(durationMs) || durationMs < 1000)
  throw new Error("scene durationMs invalid");

const frameCount = Math.ceil((durationMs / 1000) * fps);
const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "hps-slide-"));
const framesDir = path.join(workDir, "frames");
fs.mkdirSync(framesDir);

function ffmpeg(args) {
  const result = spawnSync("ffmpeg", args, { encoding: "utf8" });
  if (result.status !== 0)
    throw new Error("ffmpeg failed: " + (result.stderr || "").slice(-800));
}

function ffprobeJson(target) {
  const result = spawnSync(
    "ffprobe",
    ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", target],
    { encoding: "utf8" },
  );
  if (result.status !== 0)
    throw new Error("ffprobe failed: " + (result.stderr || "").slice(-400));
  return JSON.parse(result.stdout);
}

(async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await page.goto(pathToFileURL(path.join(root, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 20000 });
    const applied = await page.evaluate((s) => window.visualPlayer.apply(s), scene);
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
    "-vf", "scale=1600:900",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-r", String(fps),
    "-c:a", "aac",
    "-b:a", "192k",
    outputPath,
  ]);
  fs.rmSync(workDir, { recursive: true, force: true });
  const probe = ffprobeJson(outputPath);
  const video = probe.streams.find((s) => s.codec_type === "video");
  const audio = probe.streams.find((s) => s.codec_type === "audio");
  if (!video || !audio) throw new Error("segment missing video or audio stream");
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
