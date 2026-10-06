// 勾画标注覆盖层:消费 props 中已解析的 annotation_timeline 事件绘制笔迹层。
// 视频呈现**栅格墨迹帧**(位图手写 PNG,由确认流程经 annotation_ink 渲染),
// 以整幅 <img> 覆盖(与墨迹帧同尺寸,无缩放);仅当旧 timeline 缺少墨迹帧
// 时回退到矢量轮廓。时间采样、每笔推进与帧索引全部来自与浏览器共享的
// annotation_playback.js(同一实现)。旧 props 缺字段时渲染为空覆盖层。

import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import AnnotationsPlayback from '../../../static/annotation_playback.js';

export type AnnotationStroke =
  | {
      kind: 'polyline';
      points: [number, number][];
    }
  | {
      kind: 'rect';
      x: number;
      y: number;
      width: number;
      height: number;
    }
  | {
      kind: 'path';
      closed?: boolean;
      points?: [number, number][];
      ink?: {
        kind: 'raster';
        frames?: string[];
        fps?: number;
        canvas?: number[];
      };
    };

export type AnnotationTimelineEvent = {
  annotation_id: string;
  start_sec: number;
  draw_end_sec: number;
  hold_end_sec: number;
  exit_end_sec: number;
  style: {
    type: string;
    color: string;
    opacity: number;
    width: number;
    padding: number;
    seed: number;
  };
  strokes: AnnotationStroke[];
};

export type AnnotationTimeline = {
  schema_version?: number;
  resolver_version?: string;
  events?: AnnotationTimelineEvent[];
  needs_review?: unknown;
};

type RasterShape = {annotationId: string; frames: string[]; frameIndex: number; opacity: number};
type VectorShape = Record<string, unknown>;

function makeVectorOnly(event: AnnotationTimelineEvent): AnnotationTimelineEvent {
  return {
    ...event,
    strokes: event.strokes.map((stroke) => {
      if (stroke.kind === 'path') {
        const {ink: _ink, ...rest} = stroke;
        void _ink;
        return rest as AnnotationStroke;
      }
      return stroke;
    }),
  };
}

export const AnnotationOverlay: React.FC<{
  timeline?: AnnotationTimeline;
}> = ({timeline}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const events = timeline?.events;
  if (!Array.isArray(events) || events.length === 0) {
    return null; // 旧 props 缺字段 → 空覆盖层
  }
  const timeSec = frame / fps;
  const rasterShapes: RasterShape[] = [];
  let vectorShapes: VectorShape[] = [];
  for (const event of events) {
    // fps 必须取视频真实帧率(R4-007):量化网格才与确认时序一致
    const state = AnnotationsPlayback.sampleEvent(event, timeSec, fps);
    if (state.phase === 'hidden') continue;
    const baseOpacity = Math.max(0, Math.min(1, Number(event.style?.opacity ?? 0.85)));
    const opacity = baseOpacity * state.opacityScale;
    (event.strokes || []).forEach((stroke, strokeIndex) => {
      if (stroke.kind === 'path' && stroke.ink?.kind === 'raster' && stroke.ink.frames?.length) {
        const frameIndex = AnnotationsPlayback.rasterFrameIndex(
          event,
          stroke,
          strokeIndex,
          state.drawProgress,
          stroke.ink.frames.length,
        );
        if (frameIndex < 0) return;
        rasterShapes.push({
          annotationId: event.annotation_id,
          frames: stroke.ink.frames,
          frameIndex,
          opacity,
        });
      }
    });
    const sampled = AnnotationsPlayback.renderScene([makeVectorOnly(event)], timeSec, fps) as VectorShape[];
    vectorShapes = vectorShapes.concat(sampled.filter((_shape, index) => {
      const stroke = event.strokes[index];
      return !(stroke?.kind === 'path' && stroke.ink?.kind === 'raster' && stroke.ink.frames?.length);
    }));
  }
  if (!rasterShapes.length && !vectorShapes.length) {
    return null;
  }
  return (
    <div style={{position: 'absolute', inset: 0, zIndex: 9000, pointerEvents: 'none'}}>
      {rasterShapes.map((shape, index) => {
        const raw = shape.frames[Math.min(shape.frameIndex, shape.frames.length - 1)];
        const src = raw.startsWith('http') || raw.startsWith('file://') ? raw : staticFile(raw);
        return (
          <Img
            key={`${shape.annotationId}-${index}`}
            src={src}
            style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: shape.opacity}}
          />
        );
      })}
      {vectorShapes.length ? (
        // viewBox 用视频真实画布(R4-007):竖屏项目不再错位
        <svg viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
          {vectorShapes.map((shape, index) => {
            const key = `${String(shape.annotationId)}-${index}`;
            if (shape.kind === 'path') {
              return (
                <path
                  key={key}
                  d={String(shape.d)}
                  fill={shape.closed ? String(shape.stroke) : 'none'}
                  fillOpacity={shape.closed ? Math.min(0.12, Number(shape.opacity) * 0.14) : 0}
                  stroke={String(shape.stroke)}
                  strokeWidth={2.5}
                  strokeLinejoin="round"
                  opacity={Number(shape.opacity)}
                />
              );
            }
            if (shape.kind === 'polyline') {
              return (
                <path
                  key={key}
                  d={String(shape.d)}
                  fill="none"
                  stroke={String(shape.stroke)}
                  strokeWidth={Number(shape.strokeWidth)}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={Number(shape.opacity)}
                />
              );
            }
            return (
              <rect
                key={key}
                x={Number(shape.x)}
                y={Number(shape.y)}
                width={Number(shape.width)}
                height={Number(shape.height)}
                fill={String(shape.fill)}
                opacity={Number(shape.opacity)}
              />
            );
          })}
        </svg>
      ) : null}
    </div>
  );
};
