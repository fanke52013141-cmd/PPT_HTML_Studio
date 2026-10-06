from dataclasses import replace
import pytest
from scripts.align_annotation_audio import map_tokens
from annotation_alignment import resolve_anchor_times
from checks.test_annotation_timeline import _item


def test_repeated_characters_keep_original_occurrence():
    text = '标注 标注'
    mapping = [{'beat_id':'b','range':[i,i+1]} if c != ' ' else None for i,c in enumerate(text)]
    items = [{'text':c,'start':n*.2,'end':n*.2+.1} for n,c in enumerate(text.replace(' ',''))]
    tokens = map_tokens(text,mapping,items,[],2)
    assert [t['range'] for t in tokens] == [[0,1],[1,2],[3,4],[4,5]]
    assert tokens[2]['start'] == .4
    assert all('score' not in t for t in tokens)


def test_repaired_expansion_invalidates_whole_original_range():
    mapping = [{'beat_id':'b','range':[0,3]}]*2
    items = [{'text':'百','start':0,'end':.1},{'text':'分','start':.1,'end':.2}]
    assert not map_tokens('百分',mapping,items,[2],2)


def test_changed_complete_transcript_is_rejected():
    with pytest.raises(ValueError):
        map_tokens('标注',[{'beat_id':'b','range':[0,1]}]*2,[{'text':'错','start':0,'end':.1}],[],1)


@pytest.mark.parametrize('start,end', [(0,0),(0,4),(float('nan'),.2)])
def test_invalid_intervals_cannot_become_tokens(start,end):
    assert not map_tokens('标',[{'beat_id':'b','range':[0,1]}],
                          [{'text':'标','start':start,'end':end}],[],1)


def test_qwen_anchor_without_fabricated_confidence_and_partial_word_rejection():
    item = _item()
    item = replace(item,anchor=replace(item.anchor,beat_id='b',range_start=0,range_end=2,quote='标注'))
    tokens = [{'beat_id':'b','range':[i,i+1],'start':i*.2,'end':i*.2+.1,
               'source':'qwen_alignment','precision':'character'} for i in range(2)]
    assert resolve_anchor_times([item],{'tokens':tokens})[item.annotation_id]['start'] == 0
    assert not resolve_anchor_times([item],{'tokens':tokens,'engine':{'engine_version':'whisperx_old'}})
    tokens = [{'beat_id':'b','range':[0,4],'start':0,'end':.5,'source':'qwen_alignment','precision':'word'}]
    assert not resolve_anchor_times([item],{'tokens':tokens})


def test_worker_cache_invalidates_old_engine_and_reuses_new_engine(tmp_path, monkeypatch):
    import json
    import threading
    from types import SimpleNamespace
    import annotation_alignment_worker as worker
    (tmp_path/'voice.mp3').write_bytes(b'audio')
    (tmp_path/'narration_beats.json').write_text('{}')
    (tmp_path/'word_alignment.json').write_text(json.dumps({'cache_key':{'engine_version':'whisperx_old'}}))
    monkeypatch.setattr(worker,'ANNOTATION_WORKER_PYTHON',__file__)
    calls=[]
    def execute(args, **kwargs):
        assert kwargs['env']['HF_HUB_OFFLINE'] == '1'
        assert kwargs['env']['PYTHONIOENCODING'] == 'utf-8'
        request=json.loads(__import__('pathlib').Path(args[args.index('--input')+1]).read_text(encoding='utf-8'))
        calls.append(request)
        response={'cache_key':request['cache_key'],'tokens':[]}
        __import__('pathlib').Path(args[args.index('--output')+1]).write_text(json.dumps(response))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(worker,'run_subprocess_bounded',execute)
    beats=[{'beat_id':'b','spoken_text':'标注'}]
    result=worker.run_alignment(tmp_path,beats,threading.Event())
    assert calls[0]['model'] == 'Qwen/Qwen3-ForcedAligner-0.6B'
    (tmp_path/'word_alignment.json').write_text(json.dumps(result))
    assert worker.run_alignment(tmp_path,beats,threading.Event()) == result
    assert len(calls) == 1
    (tmp_path/'voice.mp3').write_bytes(b'changed')
    worker.run_alignment(tmp_path,beats,threading.Event())
    assert len(calls) == 2
