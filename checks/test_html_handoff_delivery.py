"""Untrusted file packages are data, never executable or author writes."""
import base64
import io
import json
import stat
import zipfile

import pytest

from html_handoff_delivery import DeliveryError, read_delivery
from html_handoff_models import ImportRequest, SaveRequest


RESULT = {"task_id": "a" * 64, "status": "unchanged", "message": "Checked without changes", "operations": []}


def bundle(entries=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries or [("result.json", json.dumps(RESULT)), ("report.md", "# Report\nnot_run")]:
            if isinstance(name, str) and "\\" in name:
                # Windows' ZipInfo constructor normalizes separators when writing;
                # preserve an actual nonportable archive name for the rejection test.
                entry = zipfile.ZipInfo(name)
                entry.filename = name
                name = entry
            archive.writestr(name, value)
    return {"delivery_base64": base64.b64encode(stream.getvalue()).decode()}


def test_zip_json_report_and_unverified_evidence_are_bounded_data():
    result, delivery, files, raw = read_delivery(bundle())
    assert result.task_id == RESULT["task_id"] and result.status == "unchanged"
    assert delivery["report_source"] == "external_report_unverified"
    assert delivery["report_markdown"].endswith("not_run") and zipfile.is_zipfile(io.BytesIO(raw))
    assert set(files) == {"result.json", "report.md"}
    result, delivery, _, _ = read_delivery({"result": RESULT, "report_markdown": "<script>not executable</script>"})
    assert delivery["kind"] == "json" and "<script>" in delivery["report_markdown"]


@pytest.mark.parametrize("name", ["../outside.md", "evidence/../outside.txt", "C:/outside.txt", "evidence\\fake.txt",
                                 "evidence//fake.txt", "/outside.txt", "evidence/NUL.txt", "evidence/CON.png",
                                 "evidence/fake.", "index.html", "evidence/script.js", "nested/result.json"])
def test_unsafe_or_unexpected_names_are_rejected(name):
    with pytest.raises(DeliveryError):
        read_delivery(bundle([("result.json", json.dumps(RESULT)), ("report.md", "report"), (name, "no")]))


@pytest.mark.parametrize("entries", [
    [("result.json", json.dumps(RESULT))],
    [("report.md", "report")],
    [("result.json", "not json"), ("report.md", "report")],
    [("result.json", json.dumps(RESULT)), ("report.md", b"\xff")],
    [("result.json", json.dumps(RESULT)), ("report.md", "a" * 262145)],
    [("result.json", json.dumps(RESULT)), ("report.md", "report"), ("evidence/fake.png", "not png")],
    [("result.json", json.dumps(RESULT)), ("report.md", "report"), ("REPORT.MD", "duplicate")],
])
def test_missing_corrupt_oversize_and_duplicate_materials_fail(entries):
    with pytest.raises(DeliveryError):
        read_delivery(bundle(entries))


def test_symlink_and_compressed_bomb_reject_before_materialization():
    link = zipfile.ZipInfo("evidence/link.txt")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(DeliveryError):
        read_delivery(bundle([("result.json", json.dumps(RESULT)), ("report.md", "report"), (link, "../outside")]))
    with pytest.raises(DeliveryError):
        read_delivery(bundle([("result.json", json.dumps(RESULT)), ("report.md", "report"), ("evidence/huge.txt", b"0" * 2097153)]))


def test_mutually_exclusive_transport_and_save_never_accepts_zip():
    for payload in ({}, {"result": RESULT, **bundle()}, {**bundle(), "report_markdown": "foreign report"}):
        with pytest.raises(ValueError):
            ImportRequest.model_validate(payload)
    with pytest.raises(ValueError):
        SaveRequest.model_validate({**bundle(), "candidate_key": "a" * 64, "result_hash": "b" * 64})
    with pytest.raises(DeliveryError):
        read_delivery({"delivery_base64": "not base64"})
