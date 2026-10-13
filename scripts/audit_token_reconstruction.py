"""Token audit using preserved real outputs and the shared production renderer.

Calibration is an explicit, instance-only experiment; no approvals are created.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_visual_reconstruction import export_comparison
from html_reference_package import assemble_reference, design_prompt
from runtime_support import run_subprocess_killable

SOURCE = ROOT / "outputs/s08-token-flare-low-1k-1280-20261012-resume-03/runs/token-visual-revalidation"
OUT = ROOT / "outputs/token-flow-audit-20261014"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run = OUT / "run"
    visual = run / "planning/html_visual"
    manifest = json.loads((SOURCE / "planning/html_visual/resources.json").read_text(encoding="utf-8"))
    for entry in manifest["assets"]:
        destination = run / entry["file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / entry["file"], destination)
    write(visual / "resources.json", manifest)
    environment = os.environ.copy()
    environment["HPS_HTML_RESOURCES"] = str(visual / "resources.json")
    results = []
    for number in range(1, 6):
        slide = f"token-{number:02}"
        folder = OUT / slide
        folder.mkdir(exist_ok=True)
        acceptance = json.loads((SOURCE / f"planning/html_visual/candidates/{slide}/design-acceptance.json").read_text(encoding="utf-8"))
        candidate_dir = SOURCE / f"planning/html_visual/candidates/{slide}/designs" / acceptance["design_candidate_key"]
        record = json.loads((candidate_dir / "candidate.json").read_text(encoding="utf-8"))
        shutil.copy2(candidate_dir / "design-reference.png", folder / "reference.png")
        shutil.copy2(SOURCE / f"planning/html_visual/review/review-{slide}.png", folder / "before.png")
        scene = json.loads((SOURCE / f"planning/html_visual/scene-{slide}.json").read_text(encoding="utf-8"))
        write(folder / "before.scene.json", scene)
        after = copy.deepcopy(scene)
        # The measured reference is 1280x720; these edits use 1600x900 logical units.
        # Only the first page is calibrated; the other four are held-out style regressions.
        if number == 1:
            after["version"] = "0.5.0"
            edits = {
                "header-obj": {"offsetX": 4, "offsetY": 10, "typography": {"title": {"fontSizePx": 46}}},
                "intro-obj": {"offsetY": -91, "typography": {"text": {"fontSizePx": 20}}},
                "headline-obj": {"offsetY": 12, "typography": {"text": {"fontSizePx": 32}}},
                "card-1-obj": {"offsetX": 4, "offsetY": -49, "width": 676, "height": 113,
                               "typography": {"title": {"fontSizePx": 23}, "body": {"fontSizePx": 19}}},
                "card-2-obj": {"offsetX": 4, "offsetY": -27, "width": 676, "height": 113,
                               "typography": {"title": {"fontSizePx": 23}, "body": {"fontSizePx": 19}}},
                "card-3-obj": {"offsetX": 4, "offsetY": -6, "width": 676, "height": 113,
                               "typography": {"title": {"fontSizePx": 23}, "body": {"fontSizePx": 19}}},
                "subject-obj": {"offsetX": -355, "offsetY": -140, "width": 765, "height": 765},
                "figure-obj": {"offsetX": -5, "offsetY": -48, "width": 581, "height": 490,
                               "typography": {"tag": {"fontSizePx": 16}, "note": {"fontSizePx": 16}}},
                "summary-obj": {"offsetX": 4, "offsetY": 11, "width": 1475, "height": 110,
                                "typography": {"heading": {"fontSizePx": 23}, "from": {"fontSizePx": 20},
                                               "to": {"fontSizePx": 20}, "term": {"fontSizePx": 18},
                                               "takeaway": {"fontSizePx": 18}}},
            }
            for node in after["nodes"]:
                if node["id"] in edits:
                    node["presentation"] = edits[node["id"]]
            for action in after["motion"]:
                if action["targetId"] == "summary-obj" and action["type"] == "enter":
                    action["offsetY"] = 0
            write(folder / "calibration.json", {"method": "human transcription of reference geometry; not automatic extraction",
                                                 "canvas": [1600, 900], "edits": edits})
        write(folder / "after.scene.json", after)
        rendered = subprocess.run(["node", str(ROOT / "html_engine/tools/review-scene.cjs"),
                                   str(folder / "after.scene.json"), str(folder / "review.json"), str(folder / "after.png")],
                                  cwd=ROOT, env=environment, capture_output=True, text=True, timeout=180)
        review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
        if rendered.returncode or not review["passed"]:
            raise RuntimeError(f"{slide}: review failed; see {folder / 'review.json'}")
        metrics = export_comparison(folder / "reference.png", folder / "before.png", folder / "after.png", folder)
        results.append({"slide": slide, "review_passed": review["passed"], "metrics": metrics})
        print(f"{slide}: rendered and compared", flush=True)
        if number == 1:
            package = assemble_reference(record["plan"], record["brief"], repo_root=ROOT,
                                         directory=OUT / "reference-package", runner=run_subprocess_killable, run_dir=run)
            (OUT / "new-design-prompt.txt").write_text(design_prompt(package), encoding="utf-8")
            write(OUT / "new-design-input.json", {"references": package["references"], "prompt_version": "0.3.1",
                                                   "approval": "not_granted", "purpose": "new image replication check"})
    write(OUT / "results.json", results)


if __name__ == "__main__":
    main()
