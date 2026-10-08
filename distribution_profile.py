"""Read-only delivery edition profile.

`config/distribution.json` is the single source of truth for the delivery
edition. A repository checkout without that file keeps the full edition; a
file that exists but is corrupt must fail loudly at startup and never fall
back to full features.

The portable Light delivery turns off only `digital_human` and
`handwritten_annotations`. Frontend gating reads
`PPTFlow.distributionFeatures()` from `static/flow.js`; the generated
`static/distribution_profile.js` must load before `flow.js`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from repository_paths import REPO_ROOT

DISTRIBUTION_CONFIG_PATH = os.path.join(
    REPO_ROOT, "config", "distribution.json"
)

SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

FEATURE_KEYS = ("digital_human", "handwritten_annotations")

_FULL_EDITION_FEATURES: Dict[str, bool] = {
    "digital_human": True,
    "handwritten_annotations": True,
}


class DistributionProfileError(RuntimeError):
    """Raised when `config/distribution.json` exists but cannot be trusted."""


def _read_config() -> Dict[str, Any] | None:
    """Return the parsed config, or None when the checkout has none."""
    if not os.path.isfile(DISTRIBUTION_CONFIG_PATH):
        return None
    try:
        with open(DISTRIBUTION_CONFIG_PATH, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        raise DistributionProfileError(
            f"发行配置损坏，必须修复后才能启动：{DISTRIBUTION_CONFIG_PATH} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise DistributionProfileError(
            f"发行配置损坏，必须修复后才能启动：{DISTRIBUTION_CONFIG_PATH} "
            "顶层必须是对象"
        )
    return payload


def _validate(payload: Dict[str, Any]) -> Dict[str, bool]:
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise DistributionProfileError(
            f"发行配置 schema_version 不受支持：{schema_version!r}，"
            f"仅支持 {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    features = payload.get("features")
    if not isinstance(features, dict):
        raise DistributionProfileError(
            "发行配置缺少 features 对象，无法确定可用功能"
        )
    unknown = sorted(set(features) - set(FEATURE_KEYS))
    if unknown:
        raise DistributionProfileError(
            f"发行配置包含未知功能开关：{unknown}；"
            f"当前仅支持 {list(FEATURE_KEYS)}"
        )
    resolved: Dict[str, bool] = {}
    for key in FEATURE_KEYS:
        value = features.get(key, True)
        if not isinstance(value, bool):
            raise DistributionProfileError(
                f"发行配置功能开关 {key} 必须是布尔值，实际为 {value!r}"
            )
        resolved[key] = value
    return resolved


def load_profile() -> Dict[str, Any]:
    """Return the effective edition profile.

    Raises `DistributionProfileError` when a config file exists but is
    corrupt. Callers must not catch it to silently restore full features.
    """
    payload = _read_config()
    if payload is None:
        return {
            "edition": "source",
            "schema_version": None,
            "features": dict(_FULL_EDITION_FEATURES),
        }
    return {
        "edition": str(payload.get("edition") or "custom"),
        "schema_version": payload.get("schema_version"),
        "features": _validate(payload),
    }


def features() -> Dict[str, bool]:
    """Return the effective feature switches."""
    return load_profile()["features"]


def digital_human_enabled() -> bool:
    """Backend gate for the digital-human narration feature."""
    return features()["digital_human"]


def handwritten_annotations_enabled() -> bool:
    """Backend gate for the handwritten annotation feature."""
    return features()["handwritten_annotations"]


def preflight() -> Dict[str, Any]:
    """Startup preflight: surface a corrupt config as a hard failure."""
    return load_profile()
