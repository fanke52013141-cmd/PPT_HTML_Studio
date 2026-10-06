"""Regression gates for measured timing and complete multi-stroke playback."""
from dataclasses import replace
import pytest
from annotation_alignment import resolve_anchor_times, beat_times_from_alignment
from annotation_alignment_worker import normalized_transcript
from annotation_timeline import schedule_strokes, build_annotation_timeline
from checks.test_annotation_timeline import _item
from annotation_ink import render_stroke_frames
from checks.test_annotation_ink import _request


def test_selected_occurrence_uses_original_range_and_hashes():
    item = _item()
    item = replace(item, anchor=replace(item.anchor, range_start=4, range_end=6, quote="标注"))
    tokens = [{"beat_id": item.anchor.beat_id, "range": [i, i+1], "start": t, "end": t+.1,
               "precision": "character", "source": "forced_alignment", "score": .99}
              for i,t in [(0,.2),(1,.4),(4,2.1),(5,2.3)]]
    data = {"audio_hash": "a", "narration_hash": "b", "tokens": tokens}
    assert resolve_anchor_times([item], data, audio_hash="a", narration_hash="b")[item.annotation_id]["start"] == 2.1
    assert not resolve_anchor_times([item], data, audio_hash="changed")
    data["tokens"] = tokens[:-1]
    assert not resolve_anchor_times([item], data)


def test_multi_sentence_beat_keeps_first_start_last_end():
    times, _ = beat_times_from_alignment(None, {"duration_sec": 4, "segments": [
        {"beat_id": "b", "start": 0, "end": 1}, {"beat_id": "b", "start": 2, "end": 4}]})
    assert times["b"] == (0, 4)


def test_small_stroke_has_time_to_complete_and_pen_lift():
    strokes = [{"points": [[0,0],[1,0]]}, {"points": [[0,0],[1000,0]], "start_offset_sec": .06}]
    scheduled = schedule_strokes(strokes, .8)
    assert scheduled[0]["draw_end_offset_sec"] >= 2/30 - 1e-6
    assert scheduled[1]["draw_start_offset_sec"] > scheduled[0]["draw_end_offset_sec"]
    assert scheduled[1]["draw_end_offset_sec"] == pytest.approx(.8)


def test_precise_anchor_adds_audio_delay_once_and_never_anticipates():
    item = _item()
    args = dict(slide_id="slide_001", items=[item], beat_times={item.anchor.beat_id:(0,3)},
                slide_duration=5, image_hash="a", narration_hash="b", audio_hash="c",
                confirmed_input_hashes={}, audio_start_sec=.5, require_precise=True,
                anchor_times={item.annotation_id:{"start":1.011,"end":1.4,"source":"forced_alignment"}})
    payload, issues = build_annotation_timeline(**args)
    assert not issues
    assert payload["events"][0]["start_sec"] == pytest.approx(46/30)
    _, issues = build_annotation_timeline(**{**args,"anchor_times":{}})
    assert issues[0]["reason"] == "anchor_unresolved"
    _, issues = build_annotation_timeline(**args,target_ready_times={item.annotation_id:2})
    assert issues[0]["reason"] == "target_not_ready"


def test_raster_blank_first_complete_last_and_speed_profile():
    request = _request(texture=False)
    frames = render_stroke_frames(request, draw_duration_sec=.6)
    assert frames[0].getchannel("A").getbbox() is None
    assert frames[-1].getchannel("A").getbbox() is not None
    slow = render_stroke_frames(replace(request,speed_profile=(0,.9,1)),draw_duration_sec=.6)
    assert slow[len(slow)//2].tobytes() != frames[len(frames)//2].tobytes()


def test_percentage_mapping_keeps_original_codepoints():
    text, mapping = normalized_transcript([{"id":"b","spoken_text":"增长20%"}])
    assert text.startswith("增长百分之二十")
    assert len(text) == len(mapping)
    assert all(value["range"] == [2,5] for value in mapping[2:7])


def test_old_manual_point_cannot_build_until_explicit_recalibration():
    item = _item(trigger="manual", manual_start=1.234)
    item = replace(item, timing=replace(item.timing, calibration_stale=True))
    args = dict(slide_id="slide_001", items=[item], beat_times={item.anchor.beat_id:(0,3)},
                slide_duration=5, image_hash="a", narration_hash="b", audio_hash="c",
                confirmed_input_hashes={}, require_precise=True)
    payload, issues = build_annotation_timeline(**args)
    assert payload["events"] == []
    assert issues == [{"annotation_id":item.annotation_id,"reason":"manual_calibration_stale"}]
    recalibrated = replace(item, timing=replace(item.timing, calibration_stale=False))
    payload, issues = build_annotation_timeline(**{**args, "items":[recalibrated]})
    assert not issues
    assert len(payload["events"]) == 1
