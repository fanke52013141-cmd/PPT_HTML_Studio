"""Hash-sealed feature-recognition dataset transfer across machines.

export --dataset DATASET.json --output BUNDLE.zip
import --bundle BUNDLE.zip --output NEW_DIRECTORY

Transfers only files referenced by the sealed dataset (reference/request/
response/labels) plus the dataset itself. No service, provider, author write or
approval is executed; imported bytes are verified before any destination file is
created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

FORMAT = "hps.feature_recognition.bundle/0.1.0"
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_ENTRIES = 400
FORMATS = ("hps.feature_recognition_dataset",)
VERSIONS = ("0.1.0", "0.2.0")


def document(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        return False
    path = PurePosixPath(relative)
    return (bool(relative) and not path.is_absolute()
            and all(part not in ("", ".", "..") for part in relative.split("/")))


def dataset_files(dataset):
    files = {}
    for case in dataset["cases"]:
        for key in ("reference", "request", "labels", "response"):
            record = case.get(key)
            if not record:
                continue
            relative = record.get("path")
            if not safe_relative(relative):
                raise ValueError("Dataset path is unsafe: " + repr(relative))
            if relative in files and files[relative] != record["sha256"]:
                raise ValueError("Conflicting hashes for " + relative)
            files[relative] = record["sha256"]
    return files


def export_bundle(dataset_path, output):
    dataset_path, output = Path(dataset_path).resolve(), Path(output).resolve()
    if output.exists() or output == dataset_path or dataset_path in output.parents:
        raise ValueError("Use a new ZIP outside the dataset directory")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if dataset.get("format") not in FORMATS or dataset.get("version") not in VERSIONS:
        raise ValueError("Unsupported feature-recognition dataset")
    files = dataset_files(dataset)
    root = dataset_path.parent
    total = 0
    for relative, expected in files.items():
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("Dataset file escapes its root or is missing: " + relative)
        size = path.stat().st_size
        total += size
        if size > MAX_FILE or total > MAX_TOTAL or len(files) > MAX_ENTRIES:
            raise ValueError("Bundle exceeds transfer budget")
        if digest(path.read_bytes()) != expected:
            raise ValueError("Sealed input changed: " + relative)
    manifest = {
        "format": FORMAT,
        "dataset_sha256": digest(dataset_path.read_bytes()),
        "dataset_version": dataset["version"],
        "courses": sorted({case["course_id"] for case in dataset["cases"]}),
        "pages": len({(case["course_id"], case["page_id"]) for case in dataset["cases"]}),
        "files": files,
        "approvals_transferred": False,
        "provider_calls": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dataset.json", dataset_path.read_bytes())
        for relative in sorted(files):
            data = (root / relative).read_bytes()
            if digest(data) != files[relative]:
                raise ValueError("Input changed during export: " + relative)
            archive.writestr("data/" + relative, data)
        archive.writestr("manifest.json", document(manifest))
        if digest(dataset_path.read_bytes()) != manifest["dataset_sha256"]:
            raise ValueError("Input changed during export; discard incomplete bundle")
    return {"output": str(output), "files": len(files), "pages": manifest["pages"],
            "bytes": total, "sha256": digest(output.read_bytes())}


def import_bundle(bundle, output):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Import requires a new directory; existing data cannot be overwritten")
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (len(entries) > MAX_ENTRIES + 2 or len({name.casefold() for name in names}) != len(names)
                or sum(entry.file_size for entry in entries) > MAX_TOTAL
                or any(entry.file_size > MAX_FILE or stat.S_ISLNK(entry.external_attr >> 16)
                       for entry in entries)):
            raise ValueError("Duplicate, symlink or oversized archive")
        if "manifest.json" not in names or "dataset.json" not in names:
            raise ValueError("Missing manifest or dataset")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != FORMAT:
            raise ValueError("Unsupported feature-recognition bundle")
        files = manifest.get("files")
        if not isinstance(files, dict) or any(not safe_relative(p) for p in files):
            raise ValueError("Unsafe or missing file table")
        expected_names = {"manifest.json", "dataset.json"} | {"data/" + p for p in files}
        if set(names) != expected_names:
            raise ValueError("Unexpected archive members")
        dataset_bytes = archive.read("dataset.json")
        if digest(dataset_bytes) != manifest.get("dataset_sha256"):
            raise ValueError("Dataset hash mismatch")
        dataset = json.loads(dataset_bytes)
        if dataset.get("format") not in FORMATS or dataset.get("version") != manifest.get("dataset_version"):
            raise ValueError("Dataset identity mismatch")
        declared = dataset_files(dataset)
        if declared != {p: files[p] for p in declared}:
            raise ValueError("Dataset file table does not match the manifest")
        materialized = {}
        for relative, expected in files.items():
            data = archive.read("data/" + relative)
            if digest(data) != expected:
                raise ValueError("Input hash mismatch: " + relative)
            materialized[relative] = data
        output.mkdir(parents=True)
        (output / "dataset.json").write_bytes(dataset_bytes)
        for relative, data in materialized.items():
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (output / "manifest.json").write_bytes(document(manifest))
    return {"output": str(output), "files": len(files), "pages": manifest.get("pages"),
            "evaluate": f"python scripts/evaluate_feature_recognition.py --dataset {output / 'dataset.json'} --output <new-dir>"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    export = commands.add_parser("export")
    export.add_argument("--dataset", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    load = commands.add_parser("import")
    load.add_argument("--bundle", type=Path, required=True)
    load.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (export_bundle(args.dataset, args.output) if args.action == "export"
              else import_bundle(args.bundle, args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
