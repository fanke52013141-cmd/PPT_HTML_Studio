"""Bounded model evidence projection; raw checks stay authoritative on disk."""
import copy


def repair_screenshots(report):
    shots = report.get("screenshots", [])
    chosen = []
    # Prefer evidence of actual faults over an empty opening frame.
    for issue in report.get("issues", []):
        if "timeMs" not in issue or not shots:
            continue
        shot = min(shots, key=lambda s: abs(s["timeMs"] - issue["timeMs"]))
        if shot not in chosen:
            chosen.append(shot)
        if len(chosen) == 3:
            break
    for shot in reversed(shots):
        if shot not in chosen and len(chosen) < 4:
            chosen.append(shot)
    return sorted(chosen, key=lambda s: s["timeMs"])


def repair_report(report, relevant_ids=None, scope=None):
    result = {k: copy.deepcopy(v) for k, v in report.items()
              if k not in ("screenshots", "evidence_dir", "measurements_path", "frames", "relationContacts")}
    # Keep distinct object/text conflicts; collapse only repetitions across time.
    groups = {}
    issues = []
    for issue in result.get("issues", []):
        if issue.get("code") != "TEMPORAL_OVERLAP":
            issues.append(issue)
            continue
        measured = issue.get("measured", {})
        key = (tuple(sorted(issue.get("targets", []))), measured.get("reason"),
               measured.get("textRect", {}).get("part"))
        if key not in groups:
            groups[key] = {**issue, "firstTimeMs": issue.get("timeMs"),
                           "lastTimeMs": issue.get("timeMs"), "sampleCount": 0}
            issues.append(groups[key])
        groups[key]["lastTimeMs"] = issue.get("timeMs")
        groups[key]["sampleCount"] += 1
    if "issues" in result:
        result["issues"] = issues
        result["rawIssueCount"] = len(report["issues"])
    result["sampledFrameCount"] = report.get("frame_count", len(report.get("frames", [])))
    if isinstance(result.get("coverage"), dict):
        times = result["coverage"].pop("times", None)
        if times is not None:
            result["coverage"]["timeCount"] = len(times)
    if "frames" in report:
        times = {s["timeMs"] for s in repair_screenshots(report)}
        result["frames"] = [copy.deepcopy(f) for f in report["frames"] if f.get("timeMs") in times][:4]
    if relevant_ids is not None:
        # Keep every neighbour box for collision planning, but only relevant
        # text ranges/measurements and relation geometry. Raw evidence is intact.
        for key in ('reference_geometry', 'text_measurements', 'capacity_measurements'):
            if isinstance(result.get(key), dict):
                result[key] = {k: v for k, v in result[key].items() if k in relevant_ids
                               or (key == 'reference_geometry' and isinstance(v, dict) and v.get('kind') in ('arrow', 'annotation'))}
        for frame in result.get('frames', []):
            for key in ('geometry', 'textRects'):
                if isinstance(frame.get(key), dict):
                    frame[key] = {k: v for k, v in frame[key].items() if k in relevant_ids
                                  or (key == 'geometry' and isinstance(v, dict) and v.get('kind') in ('arrow', 'annotation'))}
        if 'overlapPairs' in result:
            result['checkedPairCount'] = len(result['overlapPairs'])
            result['overlapPairs'] = [p for p in result['overlapPairs'] if set(p) & set(scope or relevant_ids)]
    return result
