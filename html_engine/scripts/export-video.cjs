"use strict";
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const { spawn, execFileSync } = require("child_process");
const { once } = require("events");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");
const { compile } = require("../src/compiler.cjs");
const root = path.resolve(__dirname, "..");

async function main() {
  const sceneFile =
    process.argv[2] || path.join(root, "examples/paper-plane.scene.json");
  const scene = JSON.parse(fs.readFileSync(sceneFile, "utf8"));
  compile(scene);
  const fps = 30,
    width = 1280,
    height =
      Math.round((width * scene.canvas.height) / scene.canvas.width / 2) * 2;
  const frameCount = Math.ceil((scene.durationMs * fps) / 1000);
  const outputDirectory = path.join(root, "../outputs/e1");
  fs.mkdirSync(outputDirectory, { recursive: true });
  const taskId = crypto.randomUUID();
  const output = path.join(
    outputDirectory,
    `${scene.id}.r${scene.revision}.${taskId.slice(0, 8)}.mp4`,
  );
  const staging = path.join(
    outputDirectory,
    `.${scene.id}.${taskId}.pending.mp4`,
  );
  const executablePath =
    process.env.CHROME_PATH ||
    path.join(
      os.homedir(),
      "AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
    );
  const browser = await chromium.launch({ headless: true, executablePath });
  let encoder;
  try {
    const page = await browser.newPage({
      viewport: { width, height: height + 220 },
      deviceScaleFactor: 1,
    });
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.evaluate(() => window.e1Ready);
    const snapshot = await page.evaluate(
      (input) => window.e1.applyInput(input),
      scene,
    );
    await page.evaluate(
      ({ width }) => {
        const main = document.querySelector("main"),
          frame = document.querySelector("#frame");
        Object.assign(main.style, {
          maxWidth: "none",
          margin: "0",
          padding: "0",
        });
        Object.assign(frame.style, {
          width: `${width}px`,
          borderRadius: "0",
          boxShadow: "none",
        });
        window.e1.controller.current.fit();
      },
      { width },
    );
    const frameBox = await page.locator("#frame").boundingBox();
    if (
      Math.abs(frameBox.width - width) > 0.1 ||
      Math.abs(frameBox.height - height) > 0.1
    )
      throw new Error(
        "Output frame dimensions do not fit requested 1280 px raster; use compatible canvas aspect ratio",
      );
    encoder = spawn(
      "ffmpeg",
      [
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-framerate",
        String(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        staging,
      ],
      { stdio: ["pipe", "ignore", "pipe"] },
    );
    const closed = once(encoder, "close");
    let encoderError = "";
    encoder.stderr.on(
      "data",
      (data) => (encoderError = (encoderError + data.toString()).slice(-4000)),
    );
    encoder.stdin.on("error", () => {});
    for (let i = 0; i < frameCount; i++) {
      await page.evaluate(
        (t) => window.e1.controller.renderAt(t),
        (i * 1000) / fps,
      );
      const png = await page.locator("#frame").screenshot();
      if (encoder.exitCode !== null)
        throw new Error("Encoder stopped: " + encoderError);
      if (!encoder.stdin.write(png)) await once(encoder.stdin, "drain");
      if (i % 90 === 0) console.log(`${scene.id}: ${i}/${frameCount} frames`);
    }
    encoder.stdin.end();
    const [code] = await closed;
    if (code !== 0) throw new Error(encoderError);
    const probe = JSON.parse(
      execFileSync(
        "ffprobe",
        [
          "-v",
          "error",
          "-count_frames",
          "-show_streams",
          "-show_format",
          "-of",
          "json",
          staging,
        ],
        { maxBuffer: 1024 * 1024 },
      ),
    );
    const video = probe.streams[0];
    if (
      probe.streams.length !== 1 ||
      video.width !== width ||
      video.height !== height ||
      Number(video.nb_read_frames) !== frameCount ||
      video.r_frame_rate !== `${fps}/1`
    )
      throw new Error("Encoded video parameters differ from plan");
    if (Math.abs(Number(probe.format.duration) - frameCount / fps) > 0.001)
      throw new Error("Encoded duration differs from ceil frame count");
    execFileSync("ffmpeg", ["-v", "error", "-i", staging, "-f", "null", "-"], {
      maxBuffer: 1024 * 1024,
    });
    const evidence = {
      date: "2026-10-07",
      sourceId: scene.id,
      taskId,
      publicationPolicy:
        "new versioned file per export; staging promoted only after verification",
      sourceRevision: scene.revision,
      inputFingerprint: snapshot.inputFingerprint,
      engineVersion: "0.1.0",
      width,
      height,
      fps: { numerator: fps, denominator: 1 },
      frameCount,
      sourceDurationMs: scene.durationMs,
      encodedDurationSeconds: Number(probe.format.duration),
      frameTime: "i*1000/30 ms; final still is independently at durationMs",
      codec: "H.264",
      audio: false,
      browser: browser.version(),
      sha256: crypto
        .createHash("sha256")
        .update(fs.readFileSync(staging))
        .digest("hex"),
      localOutput: path
        .relative(path.resolve(root, ".."), output)
        .replace(/\\/g, "/"),
      verification:
        "ffprobe frame count/size/rate/duration and complete ffmpeg decode passed",
      publication: "MP4 stays local, not committed",
    };
    if (fs.existsSync(output)) throw new Error("Output task ID collision");
    fs.renameSync(staging, output);
    fs.writeFileSync(
      path.join(root, "evidence", "video-" + scene.id + ".json"),
      JSON.stringify(evidence, null, 2) + "\n",
    );
    console.log("Created " + output);
  } finally {
    if (encoder && encoder.exitCode === null) {
      const stopped = once(encoder, "close");
      encoder.kill();
      await stopped;
    }
    if (fs.existsSync(staging)) fs.unlinkSync(staging);
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
