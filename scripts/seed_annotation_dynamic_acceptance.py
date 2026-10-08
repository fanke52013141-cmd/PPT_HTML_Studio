"""Create two ratio variants of a real-audio dynamic Mask fixture."""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'outputs/annotation-bcd/isolated'
os.environ['PPT_STUDIO_DB_PATH'] = str(OUT / 'projects.db')
os.environ['PPT_STUDIO_RUNS_DIR'] = str(OUT / 'runs')


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    from database import SessionLocal, Project
    from canvas_profile_service import write_project_canvas_snapshot
    from visual_provenance import write_visual_provenance
    from PIL import Image
    source = OUT / 'runs/annotation_bcd_acceptance'
    for portrait in (False, True):
        pid = 'annotation_dynamic_' + ('portrait' if portrait else 'landscape')
        run = OUT / 'runs' / pid
        if (run / 'planning/visual_contract.json').exists():
            print(pid, 'already seeded')
            continue
        slide = run / 'slides/slide_001'
        slide.mkdir(parents=True)
        src = source / 'slides/slide_001'
        for name in ('voice.mp3', 'narration_beats.json', 'word_alignment.json', 'tts_text.txt', 'tts_metadata.json', 'subtitles.srt', 'audio_timeline.json'):
            shutil.copy2(src / name, slide / name)
        page = json.loads((src / 'annotations.json').read_text(encoding='utf-8'))
        page['revision'] = 1
        size = (1080, 1920) if portrait else (1920, 1080)
        sx, sy = (0.5625, 0.5625) if portrait else (1, 1)
        dy = 400 if portrait else 0
        master = Image.open(src / 'visual_draft.png').convert('RGB')
        if portrait:
            image = Image.new('RGB', size, 'white')
            image.paste(master.resize((1080, 608)), (0, dy))
        else:
            image = master
        image.save(slide / 'visual_draft.png')
        groups = []
        # Full nonoverlapping bands retain the title and both narrated objects.
        # The original objects sit side by side, so use full-width vertical
        # partitions for target ownership, with a separate title band.
        rectangles = [('title', 0, 0, 1920, 300, 0),
                      ('manual', 0, 300, 960, 780, 4.5),
                      ('smart', 960, 300, 960, 780, 8)]
        for gid, x, y, w, h, at in rectangles:
            left, top = round(x*sx), round(y*sy+dy)
            right, bottom = round((x+w)*sx), min(size[1], round((y+h)*sy+dy))
            groups.append({'id': gid, 'role': 'content_body', 'link_to_narration': False,
                           'manual_mask': {'rle': {'encoding': 'row_runs_v1', 'width': size[0], 'height': size[1],
                                                  'runs': [[yy, left, right] for yy in range(top, bottom)]}},
                           'reveal': {'type': 'fade_in', 'at': at, 'duration': .4}})
        for i, item in enumerate(page['items']):
            item['status']['content'] = 'draft'
            item.pop('confirmed_inputs', None)
            item['target'].update(kind='region', token_ids=[], layout_revision=None, granularity='region', quote=None,
                                  mask_group_ids=['manual' if i == 0 else 'smart'])
            item['target']['polygons'] = [[[round(x*sx), round(y*sy+dy)] for x,y in polygon] for polygon in item['target']['polygons']]
        write(slide / 'annotations.json', page)
        write(run / 'planning/visual_contract.json', json.loads((source / 'planning/visual_contract.json').read_text(encoding='utf-8')))
        write(run / 'reveal_manifest.json', {'version': 'reveal_v1', 'canvas': {'width': size[0], 'height': size[1], 'background': '#FEFDF9'},
              'slides': [{'slide_id': 'slide_001', 'slide_dir': str(slide), 'master': str(slide / 'visual_draft.png'), 'groups': groups}]})
        write(run / 'planning/annotation_settings.json', {'schema_version': 1, 'revision': 1, 'enabled': True})
        project = Project(id=pid, name=pid+'-隔离验收', run_dir=str(run), account_id='default', current_step=10,
                          canvas_profile='portrait_9_16' if portrait else 'landscape_16_9', presentation_mode='reveal', mask_enabled=1,
                          step_status=json.dumps({str(i): 'completed' for i in range(1, 8)}))
        with SessionLocal() as db:
            db.add(project)
            db.commit()
            write_project_canvas_snapshot(project)
        write_visual_provenance(run, 'slide_001', image_path=slide / 'visual_draft.png', provider='manual_upload', source_type='manual_upload')
        print(pid, 'seeded', flush=True)


if __name__ == '__main__':
    main()
