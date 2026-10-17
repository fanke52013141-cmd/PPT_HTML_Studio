"""Compare a registered frozen HTML video against identical-time preview frames.

Read-only diagnostic: does not grant approvals or register/publish artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def decode_audio(path):
    import numpy as np
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vn',
                                    '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], timeout=60)
    return np.frombuffer(data, dtype='<f4').astype('float64')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    from PIL import Image, ImageChops, ImageStat
    from html_export_snapshot import verify_course, page_folder, export_env, verify_runtime_identity
    from html_build_snapshot import fresh_hash
    from html_render_runner import HtmlRenderRunner, HtmlRenderRunnerDependencies
    from html_frozen_video import validate_video
    metadata = json.loads(args.video.with_suffix(args.video.suffix+'.render.json').read_text(encoding='utf-8'))
    evidence = metadata['export_evidence']
    course = Path(evidence['course_path'])
    manifest = verify_course(course)
    verify_runtime_identity(evidence['runtime'])
    production = HtmlRenderRunner(HtmlRenderRunnerDependencies(ROOT, lambda _: []))
    fps = evidence['validation']['fps']
    _, validation = validate_video(production, args.video, fps, evidence['validation']['frames'])
    assert validation['sha256'] == evidence['validation']['sha256']
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    comparisons = []
    for page, receipt in zip(manifest['pages'], evidence['pages'], strict=True):
        assert page['slide_id'] == receipt['slide_id']
        frozen = page_folder(course, page)
        scene = json.loads((frozen/'input/scene.json').read_text(encoding='utf-8'))
        times = {0, scene['durationMs']}
        for beat in scene['beats']:
            times.update([beat['startMs'], (beat['startMs']+beat['endMs'])/2, beat['endMs']-1])
        for action in scene['motion']:
            times.update([action['startMs'], action['startMs']+action['durationMs']])
        indices = {min(receipt['frames']-1, max(0, round(t*fps/1000))) for t in times}
        indices.add(receipt['frames']-1)
        indices = sorted(indices)
        seek_times = [min(scene['durationMs'], round(i*1000/fps)) for i in indices]
        folder = output/page['slide_id']
        folder.mkdir()
        (folder/'times.json').write_text(json.dumps(seek_times), encoding='utf-8')
        env = export_env(ROOT, frozen, production._media_env())
        env['HPS_CHROME'] = evidence['runtime']['browser']
        subprocess.run(['node', str(course/'tools/export-snapshots.cjs'), str(frozen/'input/scene.json'),
                        str(folder/'times.json'), str(folder)], env=env, check=True, capture_output=True, timeout=120)
        for number, index in enumerate(indices):
            target = folder/f'video-{number:03d}.png'
            global_index = receipt['offset_frames']+index
            subprocess.run(['ffmpeg','-v','error','-i',str(args.video),'-vf',f'select=eq(n\\,{global_index})',
                            '-frames:v','1',str(target)],check=True,capture_output=True,timeout=30)
            with Image.open(folder/f'snapshot-{number:03d}.png') as preview, Image.open(target) as video:
                assert preview.size == video.size == (1600,900)
                error = sum(ImageStat.Stat(ImageChops.difference(preview.convert('RGB'),video.convert('RGB'))).mean)/3
                comparisons.append({'slide_id':page['slide_id'],'frame':global_index,'time_ms':seek_times[number],'rgb_mean_error':error})
                assert error < 4, comparisons[-1]
        print(json.dumps({'slide':page['slide_id'],'frames_compared':len(indices)}),flush=True)
    audio = {'status':'not_run', 'reason':'multi-page signal concatenation requires separate alignment'}
    if len(manifest['pages']) == 1:
        import numpy as np
        source = decode_audio(page_folder(course,manifest['pages'][0])/'audio/voice.mp3')
        encoded = decode_audio(args.video)
        length = min(len(source),len(encoded))
        assert length > 48000 and np.mean(source**2) > 1e-8
        correlation = float(np.corrcoef(source[:length],encoded[:length])[0,1])
        # Diagnostic cross-correlation reveals codec delay instead of hiding it by aligning.
        window = min(length, 240000)
        fft_size = 1 << (2*window-1).bit_length()
        cross = np.fft.irfft(np.fft.rfft(encoded[:window],fft_size)*np.conj(np.fft.rfft(source[:window],fft_size)),fft_size)
        lags = np.arange(-4800,4801)
        lag = int(lags[np.argmax(cross[lags % fft_size])])
        audio_passed = math.isfinite(correlation) and correlation > .97 and abs(lag) <= 48000/fps
        audio = {'status':'passed' if audio_passed else 'failed','sample_rate':48000,'sample_count':length,
                 'zero_lag_correlation':correlation,'lag_samples':lag,'lag_ms':lag/48,
                 'scope':'signal preservation; not listening or transcript approval'}
    report = {'status':'failed' if audio['status']=='failed' else 'passed','video_sha256':fresh_hash(args.video),'snapshot_id':manifest['snapshot_id'],
              'validation':validation,'frames':comparisons,'audio':audio,
              'limits':'Finite frame samples; not an aesthetic or semantic approval.'}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'compared':len(comparisons),'audio':audio}),flush=True)
    assert report['status']=='passed', audio


if __name__ == '__main__':
    main()
