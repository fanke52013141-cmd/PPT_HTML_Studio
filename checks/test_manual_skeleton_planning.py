import pytest

from storyboard_planning import PlanningError, compose_manual_skeleton_slides


def test_manual_skeleton_preserves_narration_and_explicit_identity():
    source = [{'slide_id':'custom', 'main_title':' 标题 ', 'narration':' 条件成立时才结冰。 '},
              {'main_title':'下一页', 'narration':'保持限定。'}]
    slides = compose_manual_skeleton_slides(source)
    assert source[0]['main_title'] == ' 标题 '
    assert slides[0]['slide_id'] == 'custom'
    assert slides[1]['slide_id'] == 'slide_002'
    assert slides[0]['visual_groups'] == []
    assert slides[0]['narration_beats'][0]['spoken_text'] == '条件成立时才结冰。'
    assert slides[0]['narration_beats'][0]['id'] == 'custom_beat_001'


@pytest.mark.parametrize('title,narration', [(' ', '正文'), ('标题', ' ')])
def test_manual_skeleton_invalid_content_is_a_pure_planning_error(title,narration):
    with pytest.raises(PlanningError):
        compose_manual_skeleton_slides([{'main_title':title,'narration':narration}])
