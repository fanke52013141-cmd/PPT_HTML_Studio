"use strict";
const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto");
const { PNG } = require("pngjs");
const root = path.resolve(__dirname, "..");
function read(file) {
  const actual = fs.realpathSync(path.join(root, file)),
    base = fs.realpathSync(path.join(root, "assets"));
  if (path.dirname(actual) !== base) throw Error("ASSET_PATH_OUTSIDE_PACKAGE");
  const bytes = fs.readFileSync(actual);
  if (
    bytes.length < 24 ||
    bytes.readUInt32BE(16) * bytes.readUInt32BE(20) > 16000000
  )
    throw Error("ASSET_PIXEL_BUDGET");
  return { bytes, png: PNG.sync.read(bytes) };
}
function audit(file) {
  const { bytes, png } = read(file);
  const bounds = (threshold) => {
    let x = png.width,
      y = png.height,
      r = -1,
      b = -1,
      count = 0;
    for (let j = 0; j < png.height; j++)
      for (let i = 0; i < png.width; i++)
        if (png.data[(j * png.width + i) * 4 + 3] >= threshold) {
          x = Math.min(x, i);
          y = Math.min(y, j);
          r = Math.max(r, i);
          b = Math.max(b, j);
          count++;
        }
    return {
      x,
      y,
      width: r < 0 ? 0 : r - x + 1,
      height: b < 0 ? 0 : b - y + 1,
      opaqueFraction: count / (png.width * png.height),
    };
  };
  const all = bounds(1),
    main = bounds(16);
  return {
    file,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    intrinsic: { width: png.width, height: png.height },
    alphaNonzero: all,
    alpha16: main,
    marginRatio: {
      left: main.x / png.width,
      top: main.y / png.height,
      right: (png.width - main.x - main.width) / png.width,
      bottom: (png.height - main.y - main.height) / png.height,
    },
    edgeTouches:
      all.x === 0 ||
      all.y === 0 ||
      all.x + all.width === png.width ||
      all.y + all.height === png.height,
    reviewStatus: "conditional-experiment",
    anchor: { id: "frame-center", x: 0.5, y: 0.5 },
    limitations:
      "Metrics do not establish clean contour, correct science or aesthetic approval",
  };
}
function crop(manifest) {
  if (
    manifest.version !== "0.1.0" ||
    !Array.isArray(manifest.slots) ||
    !manifest.slots.length
  )
    throw Error("CROP_MANIFEST");
  const { png } = read(manifest.source);
  const ids = new Set();
  const prepared = manifest.slots.map((slot) => {
    if (!/^[a-z][a-z0-9.-]*$/.test(slot.id) || ids.has(slot.id))
      throw Error("CROP_SLOT_ID");
    ids.add(slot.id);
    if (
      !/^assets\/[a-z0-9.-]+\.png$/.test(slot.output) ||
      fs.existsSync(path.join(root, slot.output))
    )
      throw Error("CROP_OUTPUT_EXISTS_OR_INVALID");
    const { x, y, width, height } = slot.rect;
    if (
      ![x, y, width, height].every(Number.isInteger) ||
      x < 0 ||
      y < 0 ||
      width < 1 ||
      height < 1 ||
      x + width > png.width ||
      y + height > png.height
    )
      throw Error("CROP_RECT");
    return slot;
  });
  const outputs = new Set(prepared.map((s) => s.output));
  if (outputs.size !== prepared.length) throw Error("CROP_DUPLICATE_OUTPUT");
  for (const slot of prepared) {
    const out = new PNG({ width: slot.rect.width, height: slot.rect.height });
    PNG.bitblt(
      png,
      out,
      slot.rect.x,
      slot.rect.y,
      slot.rect.width,
      slot.rect.height,
      0,
      0,
    );
    fs.writeFileSync(path.join(root, slot.output), PNG.sync.write(out), {
      flag: "wx",
    });
  }
  return prepared.map((s) => ({
    ...s,
    source: manifest.source,
    resource: audit(s.output),
  }));
}
if (require.main === module) {
  const [mode, ...args] = process.argv.slice(2);
  if (mode === "audit") console.log(JSON.stringify(args.map(audit), null, 2));
  else if (mode === "crop") {
    const m = JSON.parse(fs.readFileSync(args[0], "utf8"));
    console.log(JSON.stringify(crop(m), null, 2));
  } else throw Error("Use audit assets/*.png or crop manifest.json");
}
module.exports = { audit, crop };
