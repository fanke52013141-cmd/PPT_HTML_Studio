"use strict";
// Shared Python resolution for checks that spawn a fixture bridge process.
// CI installs dependencies globally (no .venv), so an explicit interpreter from
// the caller wins, then the repository virtualenv, then PATH.
const fs = require("node:fs");
const path = require("node:path");

function pythonExecutable(root = path.resolve(__dirname, "..")) {
  const explicit = process.env.PPT_STUDIO_PYTHON;
  if (explicit) {
    if (!fs.existsSync(explicit)) {
      throw new Error("PPT_STUDIO_PYTHON_MISSING: " + explicit);
    }
    return explicit;
  }
  const candidates =
    process.platform === "win32"
      ? [path.join(root, ".venv/Scripts/python.exe"), "python.exe", "python"]
      : [path.join(root, ".venv/bin/python"), "python3", "python"];
  for (const candidate of candidates) {
    if (!path.isAbsolute(candidate)) return candidate;
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error("PYTHON_NOT_FOUND: configure PPT_STUDIO_PYTHON");
}

module.exports = { pythonExecutable };
