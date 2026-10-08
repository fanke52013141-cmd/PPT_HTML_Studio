// static/annotation_playback.js 的 TypeScript 声明(UMD 共享采样实现)。
export declare const FRAME_SEC: number;
export declare function quantize(timeSec: number): number;
export declare function sampleEvent(
  event: unknown,
  timeSec: number,
  fps?: number,
): { phase: 'hidden' | 'drawing' | 'hold' | 'exit'; pathProgress: number; opacityScale: number; drawProgress: number };
export declare function strokeProgress(event: unknown, stroke: unknown, index: number, drawProgress: number): number;
export declare function rasterFrameIndex(
  event: unknown,
  stroke: unknown,
  index: number,
  drawProgress: number,
  frameCount: number,
): number;
export declare function strokeOutlinePath(
  points: Array<[number, number]>,
  widthProfile: Array<number> | null,
  baseWidth: number,
  upTo: number,
): string;
export declare function renderScene(events: unknown, timeSec: number, fps?: number): Array<Record<string, any>>;
export declare function polylinePathUpTo(points: Array<[number, number]>, progress: number): string;
export declare function polylineArcLengths(points: Array<[number, number]>): number[];
export declare function polylineTotalLength(points: Array<[number, number]>): number;
