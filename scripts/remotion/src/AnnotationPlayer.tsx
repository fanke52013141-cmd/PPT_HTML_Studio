import React from 'react';
import {createRoot, Root} from 'react-dom/client';
import {Player, PlayerRef} from '@remotion/player';
import {ArticleVideo, ArticleVideoProps} from './Video';

let root: Root | null = null;
let player: PlayerRef | null = null;
const api = {
  mount(node: HTMLElement, props: ArticleVideoProps, fps: number, duration: number, width: number, height: number) {
    api.stop();
    root = createRoot(node);
    root.render(<Player component={ArticleVideo} inputProps={props}
      ref={(ref) => {player = ref;}}
      compositionWidth={width} compositionHeight={height} fps={fps}
      durationInFrames={Math.max(1, Math.ceil(duration * fps))}
      controls autoPlay={false} showVolumeControls playbackRate={1}
      style={{width: '100%', maxHeight: '70vh'}} />);
  },
  stop() {player?.pause(); root?.unmount(); root = null; player = null;},
  frame() {return player?.getCurrentFrame() ?? 0;},
  pause() {player?.pause();},
  seek(frame: number) {player?.seekTo(frame);},
};
(window as unknown as {AnnotationPlayer: typeof api}).AnnotationPlayer = api;
