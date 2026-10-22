/*
 * Deterministic asset-sheet layout for the illustration batching panel.
 *
 * The sheet is a fixed grid of transparent cells. Subjects are required to stay
 * inside their own cell, so the extractor can cut exact PNGs without guessing
 * ownership from pixels. The layout only chooses geometry; it never approves
 * generated assets or registers them.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AssetSheetLayout = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const LIMIT = 4;
  const MARGIN = 24;
  const GUTTER = 24;
  const MIN_CELL = 64;

  function dimensionsFor(orientation) {
    if (orientation === 'portrait') return [864, 1536]; // 9:16
    if (orientation === 'square') return [1024, 1024]; // 1:1
    return [1536, 864]; // 16:9
  }

  function gridFor(count, orientation) {
    if (count <= 1) return [1, 1]; // cols, rows
    if (count === 2) return orientation === 'portrait' ? [1, 2] : [2, 1];
    return [2, 2];
  }

  function plan(needs, options = {}) {
    if (!Array.isArray(needs) || !needs.length || needs.length > LIMIT) {
      throw new Error('每行填写一个配图需求，共1至4个');
    }
    const cleaned = needs.map((value) => String(value == null ? '' : value).trim());
    if (cleaned.some((value) => !value || value.length > 1000)) {
      throw new Error('每项需求需为1至1000字');
    }
    const orientation = ['landscape', 'portrait', 'square'].includes(options.orientation)
      ? options.orientation : 'landscape';
    const [width, height] = dimensionsFor(orientation);
    const [columns, rows] = gridFor(cleaned.length, orientation);
    const usableWidth = width - MARGIN * 2 - (columns - 1) * GUTTER;
    const usableHeight = height - MARGIN * 2 - (rows - 1) * GUTTER;
    const cellWidth = Math.floor(usableWidth / columns);
    const cellHeight = Math.floor(usableHeight / rows);
    if (cellWidth < MIN_CELL || cellHeight < MIN_CELL) {
      throw new Error('素材板格子过小，请减少数量或换方向');
    }
    const method = options.method === 'boundary_color' ? 'boundary_color' : 'source_alpha';
    const stamp = options.stamp == null ? Date.now() : String(options.stamp);
    const slots = cleaned.map((need, index) => {
      const slot = {
        id: `slot-${index + 1}`,
        asset_id: `sheet-${stamp}-${index + 1}`,
        role: '独立主体配图',
        need,
        rect: [
          MARGIN + (index % columns) * (cellWidth + GUTTER),
          MARGIN + Math.floor(index / columns) * (cellHeight + GUTTER),
          cellWidth,
          cellHeight,
        ],
        method,
      };
      if (method === 'boundary_color') slot.background = { rgb: [255, 255, 255], tolerance: 16 };
      if (method === 'source_alpha' && options.cleanup) {
        slot.alpha_cleanup = { threshold: 1, guard_radius: 2, max_removed_fraction: 0.02 };
      }
      return slot;
    });
    return {
      format: 'hps.html.asset_sheet.plan',
      version: '0.1.0',
      id: 'illustrations',
      width,
      height,
      direction: 'V05',
      slots,
    };
  }

  return { plan, dimensionsFor, LIMIT, MARGIN, GUTTER };
}));
