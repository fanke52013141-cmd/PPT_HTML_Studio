"""One explicitly authorized low/1K image call; refuse accidental repeats."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/token-flow-audit-20261014"
script = Path(r"C:\Users\Administrator\.agents\skills\toapis-image-gen\scripts\gen_image.py")
target = OUT / "new-generated-design.png"
if target.exists() or (OUT / "new-generation.log").exists():
    raise SystemExit("Existing result/request log preserved; inspect it before retrying.")
data = json.loads((OUT / "new-design-input.json").read_text(encoding="utf-8"))
prompt = (OUT / "new-design-prompt.txt").read_text(encoding="utf-8")
command = [sys.executable, str(script), "--prompt", prompt, "--out", str(target),
           "--size", "16:9", "--quality", "low", "--resolution", "1k"]
for reference in data["references"]:
    command += ["--ref", reference]
with (OUT / "new-generation.log").open("w", encoding="utf-8") as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
print(json.dumps({"exit_code": result.returncode, "output_exists": target.exists(),
                  "model": "gpt-image-2-vip", "quality": "low", "resolution": "1k"}))
raise SystemExit(result.returncode)
