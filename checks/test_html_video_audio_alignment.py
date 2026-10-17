"""Real AAC priming regression: non-silent page-local chirps, no TTS/provider."""
import subprocess
from pathlib import Path

import numpy as np
import pytest

from html_render_runner import HtmlRenderRunner, HtmlRenderRunnerDependencies
from html_frozen_video import validate_video
from scripts.verify_html_video_frames import decode_audio


@pytest.mark.parametrize('page_count', [1, 3])
def test_concat_preserves_decoded_audio_zero_time_and_page_boundaries(tmp_path, page_count):
    root = Path(__file__).resolve().parents[1]
    runner = HtmlRenderRunner(HtmlRenderRunnerDependencies(root, lambda _: []))
    segments, counts, expected = [], [], []
    for index, frames in enumerate([21, 27, 33][:page_count]):
        segment = tmp_path / f'page-{index}.mp4'
        duration = frames / 30
        # Chirp provides a unique time reference; plain sine admits false periodic matches.
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=white:s=1600x900:r=30:d={duration}',
                        '-f','lavfi','-i',f'aevalsrc=0.4*sin(2*PI*({200+index*350}*t+400*t*t)):s=24000:d={duration}',
                        '-c:v','libx264','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709',
                        '-color_trc','bt709','-bsf:v','h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1',
                        '-c:a','aac','-b:a','192k','-t',str(duration),str(segment)],
                       capture_output=True,check=True,timeout=30)
        segments.append(segment); counts.append(frames)
        decoded = decode_audio(segment)
        expected.append(decoded[:round(duration*48000)])
    output = tmp_path / 'course.mp4'
    runner._concat(segments, output, frame_counts=counts, fps=30)
    validate_video(runner, output, 30, sum(counts))
    if page_count == 1:
        assert output.read_bytes() == segments[0].read_bytes()
    reference, actual = np.concatenate(expected), decode_audio(output)
    assert len(actual) >= len(reference)
    assert float(np.corrcoef(reference, actual[:len(reference)])[0,1]) > .99
    offset = 0
    for frames in counts:
        length = round(frames / 30 * 48000)
        assert float(np.corrcoef(reference[offset:offset+length], actual[offset:offset+length])[0,1]) > .99
        offset += length
