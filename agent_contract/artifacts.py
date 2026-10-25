"""Artifact type system for Agent-facing resource references.

Artifacts are the files produced by the pipeline: images, audio, video, PPTX.
This module owns the artifact *utilities* (type enum, MIME mapping, resource
URIs); the Agent-facing schema models live in ``agent_contract.models`` and are
re-exported here so legacy imports keep resolving to the single source.
"""

from __future__ import annotations

from enum import Enum

from agent_contract.models import ArtifactInfo, ArtifactsListResult as ArtifactCollection

__all__ = ["ArtifactType", "ArtifactInfo", "ArtifactCollection", "mime_for_type", "build_resource_uri"]


class ArtifactType(str, Enum):
    image = "image"
    audio = "audio"
    video = "video"
    pptx = "pptx"
    contract = "contract"
    narration = "narration"
    mask = "mask"
    subtitle = "subtitle"
    other = "other"


# MIME type mapping
_MIME_MAP = {
    ArtifactType.image: "image/png",
    ArtifactType.audio: "audio/mpeg",
    ArtifactType.video: "video/mp4",
    ArtifactType.pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ArtifactType.contract: "application/json",
    ArtifactType.narration: "application/json",
    ArtifactType.mask: "application/json",
    ArtifactType.subtitle: "application/x-subrip",
    ArtifactType.other: "application/octet-stream",
}


def mime_for_type(artifact_type: str) -> str:
    """Return the default MIME type for an artifact type string."""
    try:
        at = ArtifactType(artifact_type)
        return _MIME_MAP.get(at, "application/octet-stream")
    except ValueError:
        return "application/octet-stream"


def build_resource_uri(project_id: str, artifact_type: str, slide_id: str = "") -> str:
    """Build a ppt:// resource URI for an artifact."""
    if slide_id:
        if artifact_type == ArtifactType.image:
            return f"ppt://projects/{project_id}/slides/{slide_id}/image"
        elif artifact_type == ArtifactType.audio:
            return f"ppt://projects/{project_id}/slides/{slide_id}/audio"
        elif artifact_type == ArtifactType.narration:
            return f"ppt://projects/{project_id}/slides/{slide_id}/narration"
    else:
        if artifact_type == ArtifactType.video:
            return f"ppt://projects/{project_id}/videos/latest"
        elif artifact_type == ArtifactType.pptx:
            return f"ppt://projects/{project_id}/pptx/latest"
        elif artifact_type == ArtifactType.contract:
            return f"ppt://projects/{project_id}/contract"
    return f"ppt://projects/{project_id}/artifacts/{artifact_type}"
