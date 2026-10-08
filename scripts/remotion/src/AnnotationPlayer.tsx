import React from 'react';
import {createRoot, Root} from 'react-dom/client';
import {Player, PlayerRef} from '@remotion/player';
import {ArticleVideo, ArticleVideoProps} from './Video';

let root: Root | null = null;
let player: PlayerRef | null = null;
let renderPlayer: ((rate: number) => void) | null = null;
const api = {
  mount(node: HTMLElement, props: ArticleVideoProps, fps: number, duration: number, width: number, height: number) {
    api.stop();
    root = createRoot(node);
    renderPlayer = (rate) => root?.render(<Player component={ArticleVideo} inputProps={props}
      ref={(ref) => {player = ref;}}
      compositionWidth={width} compositionHeight={height} fps={fps}
      durationInFrames={Math.max(1, Math.ceil(duration * fps))}
      controls autoPlay={false} showVolumeControls playbackRate={rate}
      style={{width: '100%', maxHeight: '70vh'}} />);
    renderPlayer(1);
  },
  stop() {player?.pause(); root?.unmount(); root = null; player = null; renderPlayer = null;},
  frame() {return player?.getCurrentFrame() ?? 0;},
  rate(rate: number) {renderPlayer?.(rate);},
  pause() {player?.pause();},
  seek(frame: number) {player?.seekTo(frame);},
};
(window as unknown as {AnnotationPlayer: typeof api}).AnnotationPlayer = api;
