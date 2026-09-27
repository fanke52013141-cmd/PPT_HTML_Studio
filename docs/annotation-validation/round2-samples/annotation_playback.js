// 勾画标注播放采样(浏览器与 Remotion 共用的唯一实现,UMD 同 flow.js)。
// 对应交接文档 7.3 与第二轮优化方案 4.5/4.6:
// - 每笔独立起止(start_offset_sec),跨行按阅读顺序推进,不共享 progress;
// - 手写轮廓 = 中心线 + width_profile → 笔迹轮廓(法向偏移闭合多边形),
//   起收笔变细、退出淡出连续、0% 真正不可见;
// - 速度轮廓 speed_profile 把时间进度映射到弧长(起笔缓/主体快/收笔减速);
// - 时间量化接收实际 fps(默认 30);禁止 Math.random/当前时间/网络。

(function attachAnnotationPlayback(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  root.AnnotationsPlayback = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function createAnnotationPlayback() {
  const DEFAULT_FPS = 30;
  const EPS = 0.0001;

  function round2(value) {
    return Math.round(value * 100) / 100;
  }

  // ------------------------------------------------------------ 弧长工具

  function polylineArcLengths(points) {
    const lengths = [0];
    for (let i = 1; i < points.length; i += 1) {
      const dx = points[i][0] - points[i - 1][0];
      const dy = points[i][1] - points[i - 1][1];
      lengths.push(lengths[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    return lengths;
  }

  function polylineTotalLength(points) {
    if (!points || points.length < 2) return 0;
    return polylineArcLengths(points)[points.length - 1];
  }

  // ------------------------------------------------------------ 时间量化

  // 帧量化:接收实际 fps(25/30/60),同一帧内采样一致
  function quantize(timeSec, fps) {
    const frame = Math.max(1, Math.round(Number(fps) || DEFAULT_FPS));
    const frameSec = 1 / frame;
    return Math.floor((Math.max(0, Number(timeSec) || 0)) / frameSec) * frameSec;
  }

  // ------------------------------------------------------------ 事件采样

  // 单事件在某时刻的视觉状态(时间以页面内展示时间为准)。
  function sampleEvent(event, timeSec, fps) {
    const start = Number(event.start_sec) || 0;
    const drawEnd = Number(event.draw_end_sec) || start;
    const holdEnd = Number(event.hold_end_sec) || drawEnd;
    const exitEnd = Number(event.exit_end_sec) || holdEnd;
    const t = quantize(timeSec, fps);
    const qStart = quantize(start, fps);
    if (t < qStart) return { phase: 'hidden', pathProgress: 0, opacityScale: 0, drawProgress: 0 };
    const drawWindow = Math.max(EPS, drawEnd - start);
    const drawProgress = Math.max(0, Math.min(1, (t - start) / drawWindow));
    if (t < drawEnd) {
      return { phase: 'drawing', pathProgress: drawProgress, opacityScale: 1, drawProgress };
    }
    if (t < holdEnd) return { phase: 'hold', pathProgress: 1, opacityScale: 1, drawProgress: 1 };
    if (t < exitEnd) {
      const fade = 1 - (t - holdEnd) / Math.max(EPS, exitEnd - holdEnd);
      return { phase: 'exit', pathProgress: 1, opacityScale: Math.max(0, fade), drawProgress: 1 };
    }
    return { phase: 'hidden', pathProgress: 1, opacityScale: 0, drawProgress: 1 };
  }

  // ------------------------------------------------------------ 笔迹轮廓

  // 中心线 + width_profile → 笔迹轮廓闭合多边形(法向偏移)。
  // 仅取弧长进度 upTo(0–1)之前的部分,末端按当前法向封口(行笔中的笔尖)。
  function strokeOutlinePath(points, widthProfile, baseWidth, upTo) {
    if (!points || points.length < 2) return '';
    const clamped = Math.max(0, Math.min(1, Number(upTo) || 0));
    if (clamped <= 0) return '';
    const lengths = polylineArcLengths(points);
    const total = lengths[lengths.length - 1];
    if (total <= 0) return '';
    const target = total * clamped;
    const left = [];
    const right = [];
    let tip = null;
    for (let i = 0; i < points.length; i += 1) {
      if (lengths[i] > target + EPS) break;
      const prev = points[Math.max(0, i - 1)];
      const next = points[Math.min(points.length - 1, i + 1)];
      let nx = -(next[1] - prev[1]);
      let ny = next[0] - prev[0];
      const norm = Math.sqrt(nx * nx + ny * ny) || 1;
      nx /= norm;
      ny /= norm;
      const width = Math.max(0.4, (Number(widthProfile?.[i]) || 1) * baseWidth / 2);
      left.push([points[i][0] + nx * width, points[i][1] + ny * width]);
      right.push([points[i][0] - nx * width, points[i][1] - ny * width]);
      if (lengths[i] <= target && (i === points.length - 1 || lengths[i + 1] > target)) {
        tip = [points[i][0], points[i][1], nx, ny, width];
      }
    }
    if (left.length < 2) {
      // 极短进度:画一个笔尖圆点
      if (!tip) return '';
      return `M ${round2(tip[0] + tip[4])} ${round2(tip[1])} L ${round2(tip[0] - tip[4])} ${round2(tip[1])} Z`;
    }
    const outline = left.slice();
    // 笔尖封口:沿法向连到右侧(行进中的圆头效果)
    if (tip && clamped < 1) {
      outline.push([tip[0] + tip[2] * tip[4], tip[1] + tip[3] * tip[4]]);
    }
    for (let i = right.length - 1; i >= 0; i -= 1) outline.push(right[i]);
    if (clamped >= 1 && points[0] && (points[0][0] !== points[points.length - 1][0] || points[0][1] !== points[points.length - 1][1])) {
      outline.push(left[0]); // 开放笔(横线)闭合
    }
    const segments = outline.map((p, i) => `${i === 0 ? 'M' : 'L'} ${round2(p[0])} ${round2(p[1])}`);
    segments.push('Z');
    return segments.join(' ');
  }

  // 速度轮廓:时间进度(0–1)→ 弧长进度。
  // speed_profile 为每个弧长采样点的时间位置;反向插值求弧长。
  function arcProgressFromTime(stroke, timeProgress) {
    const profile = stroke.speed_profile;
    if (!Array.isArray(profile) || profile.length < 2) {
      return Math.max(0, Math.min(1, Number(timeProgress) || 0));
    }
    const clamped = Math.max(0, Math.min(1, Number(timeProgress) || 0));
    for (let i = 1; i < profile.length; i += 1) {
      if (profile[i] >= clamped) {
        const span = profile[i] - profile[i - 1];
        const t = span > 0 ? (clamped - profile[i - 1]) / span : 0;
        return (i - 1 + t) / (profile.length - 1);
      }
    }
    return 1;
  }

  // 单笔在某事件绘制进度下的状态:每笔独立 start_offset + 顺序分配时长。
  function strokeProgress(event, stroke, index, drawProgress) {
    const strokes = event.strokes || [];
    const startOffset = Math.max(0, Number(stroke.start_offset_sec) || 0);
    const drawWindow = Math.max(EPS, (Number(event.draw_end_sec) || 0) - (Number(event.start_sec) || 0));
    // 每笔时长 = 总绘制窗 - 各笔抬笔间隔;间隔由 start_offset 表达
    const gaps = strokes.reduce((sum, s) => sum + Math.max(0, Number(s.start_offset_sec) || 0), 0);
    const drawingTime = Math.max(EPS, drawWindow - gaps);
    const strokeCount = Math.max(1, strokes.length);
    const strokeShare = drawingTime / strokeCount;
    const elapsed = drawProgress * drawWindow;
    const strokeStart = strokes.slice(0, index).reduce(
      (sum, s) => sum + Math.max(0, Number(s.start_offset_sec) || 0) + strokeShare,
      0,
    );
    const local = (elapsed - strokeStart) / Math.max(EPS, strokeShare);
    return Math.max(0, Math.min(1, local));
  }

  // ------------------------------------------------------------ 场景渲染

  // 由事件与笔迹数据生成形状列表(纯数据;DOM/SVG 由消费方绘制)。
  // v2 path 笔迹输出轮廓多边形;旧 polyline/rect 保持兼容。
  function renderScene(events, timeSec, fps) {
    const shapes = [];
    for (const event of events || []) {
      const state = sampleEvent(event, timeSec, fps);
      if (state.phase === 'hidden') continue;
      const baseOpacity = Math.max(0, Math.min(1, Number(event.style?.opacity ?? 0.85)));
      const opacity = baseOpacity * state.opacityScale;
      const strokes = event.strokes || [];
      for (let index = 0; index < strokes.length; index += 1) {
        const stroke = strokes[index];
        if (stroke.kind === 'path') {
          const local = strokeProgress(event, stroke, index, state.drawProgress);
          const arcProgress = arcProgressFromTime(stroke, local);
          const baseWidth = Math.max(1, Number(event.style?.width) || 5);
          // 荧光笔:宽 = brush_height;轮廓用恒定宽
          const outlineWidth = stroke.brush_height ? Number(stroke.brush_height) : baseWidth;
          shapes.push({
            annotationId: event.annotation_id,
            kind: 'path',
            d: strokeOutlinePath(stroke.points, stroke.brush_height ? null : stroke.width_profile, outlineWidth, arcProgress),
            stroke: event.style.color,
            opacity,
            closed: stroke.closed === true,
          });
        } else if (stroke.kind === 'polyline') {
          shapes.push({
            annotationId: event.annotation_id,
            kind: 'polyline',
            d: polylinePathUpTo(stroke.points, state.pathProgress),
            stroke: event.style.color,
            strokeWidth: Math.max(1, Number(event.style?.width) || 5),
            opacity,
            linecap: 'round',
            linejoin: 'round',
          });
        } else if (stroke.kind === 'rect') {
          shapes.push({
            annotationId: event.annotation_id,
            kind: 'rect',
            x: stroke.x,
            y: stroke.y,
            width: stroke.width,
            height: stroke.height,
            fill: event.style.color,
            opacity,
          });
        }
      }
    }
    return shapes;
  }

  // 旧 polyline 接口(兼容 v1 数据)
  function polylinePathUpTo(points, progress) {
    if (!points || points.length < 2) return '';
    const clamped = Math.max(0, Math.min(1, Number(progress) || 0));
    if (clamped <= 0) return '';
    const lengths = polylineArcLengths(points);
    const total = lengths[lengths.length - 1];
    if (total <= 0) return '';
    const target = total * clamped;
    const segments = [`M ${points[0][0]} ${points[0][1]}`];
    for (let i = 1; i < points.length; i += 1) {
      if (lengths[i] <= target) {
        segments.push(`L ${points[i][0]} ${points[i][1]}`);
      } else {
        const segLen = lengths[i] - lengths[i - 1];
        const t = segLen > 0 ? (target - lengths[i - 1]) / segLen : 0;
        const x = points[i - 1][0] + (points[i][0] - points[i - 1][0]) * t;
        const y = points[i - 1][1] + (points[i][1] - points[i - 1][1]) * t;
        segments.push(`L ${round2(x)} ${round2(y)}`);
        break;
      }
    }
    return segments.join(' ');
  }

  return Object.freeze({
    DEFAULT_FPS,
    quantize,
    sampleEvent,
    renderScene,
    strokeOutlinePath,
    arcProgressFromTime,
    strokeProgress,
    polylinePathUpTo,
    polylineArcLengths,
    polylineTotalLength,
  });
});
