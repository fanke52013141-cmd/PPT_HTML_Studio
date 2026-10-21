"""Hash-sealed cross-machine transfer of feature-recognition datasets."""
import json
from pathlib import Path

import pytest

from scripts.evaluate_feature_recognition import evaluate
from scripts.feature_recognition_bundle import export_bundle, import_bundle

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "checks/fixtures/feature-recognition-controlled-v0.2.0/dataset.json"


def test_roundtrip_keeps_sealed_bytes_and_scores_identically(tmp_path):
    bundle = tmp_path / "bundle.zip"
    exported = export_bundle(DATASET, bundle)
    assert exported["pages"] == 2 and exported["files"] == 8
    imported = tmp_path / "imported"
    import_bundle(bundle, imported)
    original = DATASET.read_bytes()
    assert (imported / "dataset.json").read_bytes() == original
    for relative in ("course-a-request.json", "course-b-labels.json"):
        assert (imported / relative).read_bytes() == (DATASET.parent / relative).read_bytes()
    direct = evaluate(DATASET, tmp_path / "direct-score")
    roundtrip = evaluate(imported / "dataset.json", tmp_path / "roundtrip-score")
    assert roundtrip["by_provenance"] == direct["by_provenance"]
    assert roundtrip["by_ownership"] == direct["by_ownership"]
    assert roundtrip["dataset_sha256"] == direct["dataset_sha256"]


def test_tampered_member_is_rejected_before_writing(tmp_path):
    import zipfile

    bundle = tmp_path / "bundle.zip"
    export_bundle(DATASET, bundle)
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(tampered, "w") as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == "data/course-a-labels.json":
                data = data.replace(b"independent_illustration", b"independent_illustratioN")
            target.writestr(entry, data)
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="hash mismatch"):
        import_bundle(tampered, output)
    assert not output.exists()


def test_traversal_and_existing_output_are_rejected(tmp_path):
    document = json.loads(DATASET.read_text(encoding="utf-8"))
    document["cases"][0]["reference"]["path"] = "../escape.png"
    escaped = tmp_path / "escaped-dataset.json"
    escaped.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        export_bundle(escaped, tmp_path / "bundle.zip")
    bundle = tmp_path / "ok.zip"
    export_bundle(DATASET, bundle)
    output = tmp_path / "exists"
    output.mkdir()
    with pytest.raises(ValueError, match="new directory"):
        import_bundle(bundle, output)


def test_export_refuses_existing_and_missing_files(tmp_path):
    bundle = tmp_path / "bundle.zip"
    bundle.write_bytes(b"occupied")
    with pytest.raises(ValueError, match="new ZIP"):
        export_bundle(DATASET, bundle)
    import shutil

    copied = tmp_path / "copied"
    shutil.copytree(DATASET.parent, copied)
    dataset = copied / "dataset.json"
    document = json.loads(dataset.read_text(encoding="utf-8"))
    document["cases"][0]["response"]["sha256"] = "0" * 64
    dataset.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Sealed input changed"):
        export_bundle(dataset, tmp_path / "broken.zip")
