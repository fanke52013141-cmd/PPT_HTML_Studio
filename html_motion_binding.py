"""Shared stable motion identity and strict author-binding validation."""
from __future__ import annotations

import hashlib


def motion_identity(action):
    return action.get("actionId") or f"{action['targetId']}:{action['type']}"


def validate_binding(scene, binding, beat_ids):
    def fail(message):
        raise ValueError(message)
    motions = scene.get("motion")
    if not isinstance(motions, list):
        fail("Invalid motion list")
    semantic = scene.get("version") in ("0.6.0", "0.7.0")
    known = {}
    for a in motions:
        if not isinstance(a, dict) or not a.get("targetId") or not a.get("type"):
            fail("Invalid motion target/type")
        if semantic and (not isinstance(a.get("actionId"), str) or not a["actionId"]):
            fail("Missing stable actionId")
        key = motion_identity(a)
        if key in known:
            fail("Duplicate motion identity")
        known[key] = a
    if binding is None:
        if semantic:
            fail("Semantic scene requires explicit binding")
        return {}
    version = "0.2.0" if semantic else "0.1.0"
    fields = {"format", "version", "mode", "actions"} | ({"sourceBeats"} if semantic else set())
    if (not isinstance(binding, dict) or set(binding) != fields or
        binding.get("format") != "hps.html.motion_binding" or binding.get("version") != version or
        binding.get("mode") != "beat_ids" or not isinstance(binding.get("actions"), dict)):
        fail("Invalid binding format/version")
    links = binding["actions"]
    if set(links) - set(known) or (semantic and set(links) != set(known)):
        fail("Binding actions must match scene identities")
    for link in links.values():
        if (not isinstance(link, dict) or set(link) != {"beatId", "edge", "offsetMs"} or
            link.get("beatId") not in beat_ids or link.get("edge") not in ("start", "end") or
            type(link.get("offsetMs")) is not int or abs(link["offsetMs"]) > 120000):
            fail("Invalid beat binding/offset")
    if semantic:
        sources = binding["sourceBeats"]
        if not isinstance(sources, list) or not sources:
            fail("Missing authoritative spoken text")
        ids = set()
        for b in sources:
            if (not isinstance(b, dict) or set(b) != {"id", "spoken_text", "spoken_text_sha256"} or
                not isinstance(b.get("id"), str) or not b["id"] or b["id"] in ids or
                not isinstance(b.get("spoken_text"), str) or not b["spoken_text"].strip() or
                hashlib.sha256(b["spoken_text"].encode("utf-8")).hexdigest() != b.get("spoken_text_sha256")):
                fail("Invalid source beat identity/text/hash")
            ids.add(b["id"])
        if ids != beat_ids:
            fail("Source beats differ from current narration")
    return links
