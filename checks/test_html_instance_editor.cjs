"use strict";
const fs = require("fs"),
  path = require("path"),
  os = require("os"),
  assert = require("node:assert/strict");
const { spawn } = require("child_process");
const { chromium } = require("../html_engine/node_modules/playwright");
(async () => {
  const root = path.resolve(__dirname, ".."),
    run = fs.mkdtempSync(path.join(os.tmpdir(), "hps-editor-browser-"));
  const child = spawn(
    path.join(root, ".venv/Scripts/python.exe"),
    [path.join(__dirname, "test_html_scene_editor_fixture.py"), run],
    { cwd: root, windowsHide: true },
  );
  let browser,
    stderr = "";
  child.stderr.on("data", (d) => (stderr += d));
  try {
    const port = await new Promise((resolve, reject) => {
      let output = "";
      const timer = setTimeout(() => reject(Error("fixture timeout")), 30000);
      child.stdout.on("data", (d) => {
        output += d;
        try {
          const p = JSON.parse(output.trim());
          clearTimeout(timer);
          resolve(p.port);
        } catch {}
      });
      child.on("exit", (code) => {
        clearTimeout(timer);
        reject(Error(`fixture exited ${code} ${stderr}`));
      });
    });
    browser = await chromium.launch({
      headless: true,
      executablePath:
        process.env.HPS_CHROME ||
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    });
    const page = await browser.newPage({
        viewport: { width: 1500, height: 1100 },
      }),
      errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const url = `http://127.0.0.1:${port}`;
    await page.goto(url);
    await page.waitForFunction(() =>
      document
        .querySelector("[data-editor-status]")
        ?.textContent.includes("修订 1"),
    );
    await page.locator('[data-object="header"]').click();
    await page
      .getByRole("button", { name: "添加 presentation", exact: true })
      .click();
    const x = page.locator('[data-field="presentation.offsetX"]');
    await x.fill("20");
    await x.blur();
    await page
      .getByRole("button", { name: "添加 typography", exact: true })
      .click();
    const font = page.locator(
      '[data-field="presentation.typography.title.fontSizePx"]',
    );
    await font.fill("28");
    await font.blur();
    await page.getByRole("button", { name: "保存修改", exact: true }).click();
    await page.waitForFunction(() =>
      document
        .querySelector("[data-editor-status]")
        ?.textContent.includes("已保存"),
    );
    await page.reload();
    await page.waitForFunction(() =>
      document
        .querySelector("[data-editor-status]")
        ?.textContent.includes("修订 2"),
    );
    await page.locator('[data-object="header"]').click();
    assert.equal(
      await page.locator('[data-field="presentation.offsetX"]').inputValue(),
      "20",
    );
    assert.equal(
      await page
        .locator('[data-field="presentation.typography.title.fontSizePx"]')
        .inputValue(),
      "28",
    );
    const frame = page.frames().find((f) => f.url() === "about:srcdoc");
    const result = await frame.evaluate(() => {
      visualPlayer.seek(9000);
      const el = document.querySelector('[data-object-id="header"]');
      return {
        left: el.style.left,
        font: el.querySelector("h1").style.fontSize,
        version: visualPlayer.scene.version,
      };
    });
    assert.deepEqual(result, { left: "78px", font: "28px", version: "0.5.0" });
    assert.deepEqual(errors, []);
    console.log(
      JSON.stringify({
        passed: true,
        realBrowser: true,
        saveReopen: true,
        result,
      }),
    );
  } finally {
    if (browser) await browser.close();
    child.kill();
    await new Promise((resolve) => {
      if (child.exitCode !== null) resolve();
      else child.once("exit", resolve);
    });
    fs.rmSync(run, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
