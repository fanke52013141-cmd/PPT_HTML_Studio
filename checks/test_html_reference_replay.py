from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from html_reference_replay import execute_once


def test_concurrent_identical_replay_dispatches_once(tmp_path):
    entered,finish=Event(),Event()
    calls=[]
    def execute():
        calls.append(1);entered.set()
        assert finish.wait(10)
        return {'human_approval':'pending'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(execute_once,tmp_path,{'correction':'one'},execute,lambda:None)
        try:
            assert entered.wait(10)
            with pytest.raises(ValueError,match='ALREADY_SUBMITTED'):
                execute_once(tmp_path,{'correction':'one'},execute,lambda:None)
        finally:finish.set()
        assert first.result()['replay_receipt']['reused'] is False
    assert len(calls)==1
    assert execute_once(tmp_path,{'correction':'one'},execute,lambda:None)['replay_receipt']['reused'] is True


def test_abandoned_intent_or_corrupt_receipt_does_not_dispatch(tmp_path):
    (tmp_path/'attempt.json').write_text('{partial')
    with pytest.raises(ValueError,match='ALREADY_SUBMITTED'):
        execute_once(tmp_path,{},lambda:pytest.fail('no dispatch'),lambda:None)
