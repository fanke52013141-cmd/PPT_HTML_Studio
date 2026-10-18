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


def signal_metrics(reference, actual, sample_rate, fps):
    """Measure at the declared time; correlation never shifts the actual signal."""
    import numpy as np
    if len(reference) < max(16, sample_rate // 20) or np.var(reference) < 1e-8 or np.var(actual) < 1e-8:
        return {'status': 'failed', 'reason': 'insufficient_non_silent_signal'}
    correlation = float(np.corrcoef(reference, actual)[0, 1])
    window = min(len(reference), 5 * sample_rate)
    start = max(0, min(int(np.argmax(np.abs(reference))) - window // 2, len(reference) - window))
    source = reference[start:start + window]
    encoded = actual[start:start + window]
    fft_size = 1 << (2 * window - 1).bit_length()
    cross = np.fft.irfft(np.fft.rfft(encoded - encoded.mean(), fft_size)
                        * np.conj(np.fft.rfft(source - source.mean(), fft_size)), fft_size)
    limit = min(round(sample_rate / 10), window - 1, fft_size // 2 - 1)
    lags = np.arange(-limit, limit + 1)
    lag = int(lags[np.argmax(cross[lags % fft_size])])
    passed = math.isfinite(correlation) and correlation > .97 and abs(lag) <= sample_rate / fps
    return {'status': 'passed' if passed else 'failed', 'sample_count': len(reference),
            'zero_lag_correlation': correlation, 'lag_samples': lag, 'lag_ms': lag * 1000 / sample_rate}


def compare_course_audio(sources, receipts, encoded, fps, sample_rate=48000):
    """Check every page and join against frozen voice inputs and frame receipts."""
    import numpy as np
    if not sources or len(sources) != len(receipts) or not math.isfinite(fps) or fps <= 0 or sample_rate <= 0:
        raise ValueError('Invalid audio comparison schedule')
    if len({p['slide_id'] for p in receipts}) != len(receipts):
        raise ValueError('Duplicate audio page identity')
    expected, pages, ranges = [], [], []
    offset_frames = 0
    for source, receipt in zip(sources, receipts, strict=True):
        frames = receipt['frames']
        if (type(frames) is not int or frames <= 0 or type(receipt['offset_frames']) is not int
                or receipt['offset_frames'] != offset_frames):
            raise ValueError('Audio page frame schedule must be contiguous')
        begin = round(offset_frames * sample_rate / fps)
        offset_frames += frames
        end = round(offset_frames * sample_rate / fps)
        source = np.asarray(source, dtype='float64')
        if source.ndim != 1 or not np.isfinite(source).all():
            raise ValueError('Invalid source audio samples')
        budget = end - begin
        if budget <= 0:
            raise ValueError('Audio frame budget contains no samples')
        overflow = source[budget:]
        # Encoder tail padding within one frame is tolerated, not dropped speech.
        lost_speech = len(overflow) > sample_rate / fps and float(np.mean(overflow ** 2)) > 1e-8
        expected.append(np.pad(source[:budget], (0, max(0, budget - len(source)))))
        ranges.append((begin, end))
        pages.append({'slide_id': receipt['slide_id'], 'offset_samples': begin,
                      'budget_samples': budget, 'source_samples': len(source),
                      'source_overflow_samples': len(overflow), 'lost_source_signal': lost_speech})
    reference = np.concatenate(expected)
    encoded = np.asarray(encoded, dtype='float64')
    if encoded.ndim != 1 or not np.isfinite(encoded).all():
        raise ValueError('Invalid encoded audio samples')
    actual_samples = len(encoded)
    missing = reference[actual_samples:]
    missing_signal = len(missing) > 0 and float(np.mean(missing ** 2)) > 1e-8
    length_passed = (len(reference) - sample_rate / fps <= actual_samples
                     <= len(reference) + sample_rate / fps + 1024 and not missing_signal)
    actual = np.pad(encoded[:len(reference)], (0, max(0, len(reference) - actual_samples)))
    for page, (begin, end) in zip(pages, ranges, strict=True):
        page.update(signal_metrics(reference[begin:end], actual[begin:end], sample_rate, fps))
        if page['lost_source_signal']:
            page['status'] = 'failed'
    boundaries = []
    for receipt, (begin, _) in zip(receipts[1:], ranges[1:], strict=True):
        left, right = max(0, begin - sample_rate // 4), min(len(reference), begin + sample_rate // 4)
        source, signal = reference[left:right], actual[left:right]
        if float(np.mean(source ** 2)) < 1e-8:
            error = float(np.max(np.abs(signal - source)))
            measured = {'status': 'passed' if error < .002 else 'failed',
                        'signal': 'silent_window', 'max_abs_error': error}
        else:
            measured = signal_metrics(source, signal, sample_rate, fps)
        boundaries.append({'before_slide_id': receipt['slide_id'], 'offset_samples': begin, **measured})
    passed = length_passed and all(p['status'] == 'passed' for p in [*pages, *boundaries])
    result = {'status': 'passed' if passed else 'failed', 'sample_rate': sample_rate,
              'sample_count': len(reference), 'encoded_samples': actual_samples,
              'length_passed': length_passed, 'pages': pages, 'boundaries': boundaries,
              'scope': 'Voice-only signal preservation and page joins; not listening or transcript approval.'}
    if len(pages) == 1:
        result.update({k: pages[0][k] for k in ('zero_lag_correlation', 'lag_samples', 'lag_ms') if k in pages[0]})
    return result


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
    audio = compare_course_audio(
        [decode_audio(page_folder(course, page)/'audio/voice.mp3') for page in manifest['pages']],
        evidence['pages'], decode_audio(args.video), fps)
    report = {'status':'failed' if audio['status']=='failed' else 'passed','video_sha256':fresh_hash(args.video),'snapshot_id':manifest['snapshot_id'],
              'validation':validation,'frames':comparisons,'audio':audio,
              'limits':'Finite frame samples; not an aesthetic or semantic approval.'}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'compared':len(comparisons),'audio':audio}),flush=True)
    assert report['status']=='passed', audio


if __name__ == '__main__':
    main()
