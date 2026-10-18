"""Refresh missing npm license texts from their published Git commit (manual tool)."""
from pathlib import Path
import hashlib
import json
import urllib.request
import urllib.error
import subprocess

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
REPOSITORIES = {
    "@cfcs/core": "naver/cfcs", "@egjs/component": "naver/egjs-component",
    "croact": "daybrush/croact", "croact-css-styled": "daybrush/css-styled",
    "css-styled": "daybrush/css-styled", "keycon": "daybrush/keycon",
    "@xzdarcy/react-timeline-editor": "xzdarcy/react-timeline-editor",
    "@xzdarcy/timeline-engine": "xzdarcy/react-timeline-editor",
}


def read(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def main():
    folder = ROOT / "licenses"
    folder.mkdir(exist_ok=True)
    records = []
    for name, repository in REPOSITORIES.items():
        version = LOCK["packages"][f"node_modules/{name}"]["version"]
        metadata_url = f"https://registry.npmjs.org/{name}/{version}"
        metadata = json.loads(read(metadata_url))
        published_commit = metadata["gitHead"]
        commit = published_commit
        source = f"https://raw.githubusercontent.com/{repository}/{commit}/LICENSE"
        evidence_kind = "upstream_license"
        if name == "@egjs/component":
            source = metadata_url + " (published README.md, License section)"
            body = (ROOT / "node_modules/@egjs/component/README.md").read_text(encoding="utf-8")
            data = body.split("## License", 1)[1].split("```", 2)[1].strip().encode() + b"\n"
            evidence_kind = "published_readme_license"
        elif name == "croact":
            # The tarball declares MIT and carries Daybrush's copyright, but omits
            # the permission text. Retain those facts; do not invent an upstream file.
            source = metadata_url + " + published dist/croact.esm.js copyright"
            template = (ROOT / "node_modules/moveable/LICENSE").read_text(encoding="utf-8")
            data = ("MIT License\n\nCopyright (c) Daybrush\n\n" + template[template.index("Permission is hereby"):]).encode()
            evidence_kind = "mit_notice_from_declared_license_and_published_copyright"
        else:
            data = None
        try:
            if data is None:
                data = read(source)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            commit = subprocess.check_output(["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"], timeout=30).decode().split()[0]
            source = f"https://raw.githubusercontent.com/{repository}/{commit}/LICENSE"
            data = read(source)
        filename = name.replace("@", "").replace("/", "--") + ".LICENSE"
        (folder / filename).write_bytes(data)
        records.append({"package": name, "version": version, "metadata_license": metadata["license"],
                        "metadata_url": metadata_url, "published_git_head": published_commit,
                        "commit": commit, "published_commit_available": commit == published_commit,
                        "evidence_kind": evidence_kind, "source": source,
                        "file": filename, "sha256": hashlib.sha256(data).hexdigest()})
        if name == "@cfcs/core":
            notice_url = f"https://raw.githubusercontent.com/{repository}/{commit}/NOTICE"
            notice = read(notice_url)
            (folder / "cfcs.NOTICE").write_bytes(notice)
            records[-1]["notice"] = {"file": "cfcs.NOTICE", "source": notice_url,
                                      "sha256": hashlib.sha256(notice).hexdigest()}
    (folder / "records.json").write_text(json.dumps({"records": records,
        "notes": ["Timeline engine 1.0.0 npm metadata declares ISC; the published gitHead belongs to the editor monorepo whose root LICENSE is MIT. Preserve both facts; timeline is not loaded by the P1 product canvas."]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Archived {len(records)} pinned upstream license records")


if __name__ == "__main__":
    main()
