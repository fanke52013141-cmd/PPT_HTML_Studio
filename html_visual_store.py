"""HTML visual scene storage for the html visual backend.

Owns per-slide scene documents, the project revision counter used for
optimistic concurrency, and readiness reads for the HTML pipeline
(html-backend-development plan B02). Storage only: no FastAPI, no
database wiring, no rendering. Callers own transactions and HTTP
errors; a revision conflict is reported as ``HtmlVisualConflict`` so
routes can answer 409 without this module importing the application.

Layout inside one project run directory::

    planning/html_visual/revision.json      {"revision": int, ...}
    planning/html_visual/scene-<slide>.json  author scene document

Every successful content change bumps ``revision`` and records the new
document hash. An unchanged write is a no-op that must not invalidate
downstream work.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

SCENE_DIR = Path("planning") / "html_visual"
REVISION_FILE = SCENE_DIR / "revision.json"
_SLIDE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


class HtmlVisualError(Exception):
    """Storage-level rejection with a user-facing message."""


class HtmlVisualConflict(HtmlVisualError):
    def __init__(self, expected: int, current: int) -> None:
        super().__init__(
            f"场景修订已变化：期望 revision={expected}，当前 revision={current}"
        )
        self.expected = expected
        self.current = current


def validate_slide_id(slide_id: str) -> str:
    value = (slide_id or "").strip()
    if not _SLIDE_ID_PATTERN.fullmatch(value):
        raise HtmlVisualError("Slide 标识不合法")
    return value


def scene_path(run_dir: str | Path, slide_id: str) -> Path:
    return Path(run_dir) / SCENE_DIR / f"scene-{validate_slide_id(slide_id)}.json"


def revision_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / REVISION_FILE


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Same-directory temp file + os.replace so the stored bytes are exactly
    ``payload``: the recorded digest always matches the on-disk document and
    an identical re-save compares equal on the byte level."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(payload)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _document_bytes(scene: dict[str, Any]) -> bytes:
    return json.dumps(
        scene, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_revision(run_dir: str | Path) -> dict[str, Any]:
    path = revision_path(run_dir)
    if not path.is_file():
        return {"revision": 0}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        revision = int(state.get("revision", 0))
    except Exception as exc:  # corrupted counter blocks writes loudly
        raise HtmlVisualError("场景修订计数损坏，请先修复 planning/html_visual") from exc
    if revision < 0:
        raise HtmlVisualError("场景修订计数不合法")
    return {"revision": revision}


def load_scene(run_dir: str | Path, slide_id: str) -> dict[str, Any] | None:
    path = scene_path(run_dir, slide_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HtmlVisualError(f"场景文档损坏：{slide_id}") from exc


def load_scene_with_revision(
    run_dir: str | Path, slide_id: str
) -> dict[str, Any] | None:
    path = scene_path(run_dir, slide_id)
    if not path.is_file():
        return None
    revision_before = _read_revision(run_dir)["revision"]
    payload = path.read_bytes()
    revision_after = _read_revision(run_dir)["revision"]
    if revision_before != revision_after:
        raise HtmlVisualError(
            "场景正在被并发写入，请重试读取"
        )
    try:
        scene = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise HtmlVisualError(f"场景文档损坏：{slide_id}") from exc
    return {
        "scene": scene,
        "sha256": _sha256(payload),
        "revision": revision_after,
    }


def save_scene(
    run_dir: str | Path,
    slide_id: str,
    scene: dict[str, Any],
    expected_revision: int,
    *,
    lock: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    """Store one scene document under optimistic concurrency.

    Returns ``{"revision", "changed", "sha256"}``. ``changed`` is False
    when the bytes are identical: the caller must treat that as a no-op
    and not invalidate downstream artifacts.
    """
    if not isinstance(scene, dict):
        raise HtmlVisualError("场景必须是 JSON 对象")
    path = scene_path(run_dir, slide_id)
    payload = _document_bytes(scene)
    digest = _sha256(payload)
    guard = lock(Path(run_dir)) if lock else None
    if guard is not None:
        # Explicit acquire/release: the injected factory returns the lock
        # object, and a bare __exit__ without __enter__ would be a no-op.
        guard.acquire()
    try:
        current = _read_revision(run_dir)["revision"]
        if expected_revision != current:
            raise HtmlVisualConflict(expected_revision, current)
        if path.is_file():
            existing = path.read_bytes()
            if existing == payload:
                return {
                    "revision": current,
                    "changed": False,
                    "sha256": _sha256(existing),
                }
        _atomic_write_bytes(path, payload)
        _atomic_write_bytes(
            revision_path(run_dir),
            json.dumps(
                {"revision": current + 1, "last_sha256": digest},
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8"),
        )
        return {"revision": current + 1, "changed": True, "sha256": digest}
    finally:
        if guard is not None:
            guard.release()


def read_status(
    run_dir: str | Path, slide_ids: Iterable[str]
) -> dict[str, Any]:
    """Project-scoped readiness facts for the HTML pipeline."""
    state = _read_revision(run_dir)
    slides: dict[str, Any] = {}
    for slide_id in slide_ids:
        path = scene_path(run_dir, slide_id)
        if path.is_file():
            payload = path.read_bytes()
            slides[slide_id] = {
                "present": True,
                "sha256": _sha256(payload),
            }
        else:
            slides[slide_id] = {"present": False, "sha256": None}
    return {
        "revision": state["revision"],
        "slides": slides,
        "scenes_present": sum(1 for s in slides.values() if s["present"]),
        "scenes_expected": len(list(slides)),
    }
