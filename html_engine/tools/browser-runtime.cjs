"use strict";
// Shared local Chromium resolution. An explicit invalid override is an error.
const fs = require("node:fs");
const path = require("node:path");
function resolveBrowser(chromium, env = process.env, exists = fs.existsSync) {
  if (env.HPS_CHROME) {
    if (!exists(env.HPS_CHROME)) throw new Error("BROWSER_OVERRIDE_MISSING");
    return env.HPS_CHROME;
  }
  const bundled = chromium.executablePath();
  if (bundled && exists(bundled)) return bundled;
  const candidates = [];
  for (const root of [env.PROGRAMFILES, env["PROGRAMFILES(X86)"], env.ProgramFiles, env["ProgramFiles(x86)"], env.LOCALAPPDATA]) {
    if (!root) continue;
    candidates.push(path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"));
    candidates.push(path.join(root, "Google", "Chrome", "Application", "chrome.exe"));
  }
  const found = candidates.find(exists);
  if (!found) throw new Error("BROWSER_NOT_FOUND: install Playwright Chromium or configure HPS_CHROME");
  return found;
}
module.exports = { resolveBrowser };
