"use strict";

const { EngineError, diagnostic } = require("./registry.cjs");

async function sha256(bytes) {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((v) => v.toString(16).padStart(2, "0"))
    .join("");
}

async function loadResources(compiled, pack) {
  const images = new Map(),
    objectUrls = [];
  try {
    // Sequential loading bounds memory and allows deterministic cleanup on the first failure.
    for (const asset of compiled.source.assets) {
      const encoded = pack[asset.file.path];
      if (typeof encoded !== "string")
        throw new EngineError([
          diagnostic(
            "ASSET_UNAVAILABLE",
            "/assets",
            `Missing packaged bytes: ${asset.file.path}`,
          ),
        ]);
      let raw;
      try {
        raw = atob(encoded);
      } catch {
        throw new EngineError([
          diagnostic(
            "ASSET_BYTES_INVALID",
            "/assets",
            `Malformed packaged data for ${asset.id}`,
          ),
        ]);
      }
      const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
      if ((await sha256(bytes)) !== asset.file.sha256)
        throw new EngineError([
          diagnostic(
            "ASSET_HASH_MISMATCH",
            "/assets",
            `Resource bytes do not match ${asset.id}@${asset.version}`,
          ),
        ]);
      const url = URL.createObjectURL(
        new Blob([bytes], { type: asset.file.mimeType }),
      );
      objectUrls.push(url);
      const image = new Image();
      image.src = url;
      try {
        await image.decode();
      } catch {
        throw new EngineError([
          diagnostic(
            "ASSET_DECODE_FAILED",
            "/assets",
            `Cannot decode ${asset.id}`,
          ),
        ]);
      }
      if (
        image.naturalWidth !== asset.intrinsic.width ||
        image.naturalHeight !== asset.intrinsic.height
      )
        throw new EngineError([
          diagnostic(
            "ASSET_DIMENSION_MISMATCH",
            "/assets",
            `Dimensions do not match ${asset.id}`,
          ),
        ]);
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(image, 0, 0);
      const pixels = context.getImageData(
        0,
        0,
        canvas.width,
        canvas.height,
      ).data;
      let left = canvas.width,
        top = canvas.height,
        right = -1,
        bottom = -1;
      for (let y = 0; y < canvas.height; y++)
        for (let x = 0; x < canvas.width; x++) {
          if (pixels[(y * canvas.width + x) * 4 + 3] > 0) {
            left = Math.min(left, x);
            top = Math.min(top, y);
            right = Math.max(right, x);
            bottom = Math.max(bottom, y);
          }
        }
      const measured = {
        x: left,
        y: top,
        width: right - left + 1,
        height: bottom - top + 1,
      };
      const declared = asset.alphaBounds;
      if (Object.keys(measured).some((k) => measured[k] !== declared[k]))
        throw new EngineError([
          diagnostic(
            "ASSET_ALPHA_BOUNDS_MISMATCH",
            "/assets",
            `alphaBounds do not match ${asset.id}`,
          ),
        ]);
      canvas.width = canvas.height = 0;
      images.set(asset.id, image);
    }
    return {
      images,
      release() {
        objectUrls.forEach((url) => URL.revokeObjectURL(url));
      },
    };
  } catch (error) {
    objectUrls.forEach((url) => URL.revokeObjectURL(url));
    throw error;
  }
}

function fontPresent(family) {
  const ctx = document.createElement("canvas").getContext("2d");
  const probe = "知识科普 汉字 水滴 WQilm 0123456789";
  return ["monospace", "serif"].some((fallback) => {
    ctx.font = `48px ${fallback}`;
    const baseline = ctx.measureText(probe).width;
    ctx.font = `48px "${family}", ${fallback}`;
    return Math.abs(ctx.measureText(probe).width - baseline) > 0.1;
  });
}

module.exports = { sha256, loadResources, fontPresent };
