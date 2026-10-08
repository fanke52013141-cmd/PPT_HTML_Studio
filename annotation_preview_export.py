"""Transient single-page preview MP4 export using the production composition."""
from pathlib import Path
import copy, json, shutil, threading, uuid
from repository_paths import REPO_ROOT
from runtime_support import run_subprocess_killable

_EXPORT_GATE = threading.Lock()

def export_preview(slide_dir, prepared, subtitle_style=None):
    repo = Path(REPO_ROOT)
    bundle = repo / "scripts" / "remotion"
    token = uuid.uuid4().hex
    public = bundle / "public" / "runtime" / "annotation_previews" / token
    public.mkdir(parents=True)
    slide_dir = Path(slide_dir).resolve()
    output = slide_dir / "preview_exports" / (token + ".mp4")
    output.parent.mkdir(exist_ok=True)
    def asset(relative):
        source = (slide_dir / relative).resolve()
        if not source.is_relative_to(slide_dir) or not source.is_file():
            raise ValueError("预览素材不存在或路径无效")
        relative = source.relative_to(slide_dir).as_posix()
        target = public / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return "runtime/annotation_previews/" + token + "/" + relative.replace("\\", "/")
    try:
        timeline = copy.deepcopy(prepared["timeline"])
        scene = copy.deepcopy(prepared["scene"])
        for layer in scene.get("layers", []): layer["asset"] = asset(layer["asset"])
        if scene.get("canvas", {}).get("background_asset"):
            scene["canvas"]["background_asset"] = asset(scene["canvas"]["background_asset"])
        for event in timeline.get("events", []):
            for stroke in event.get("strokes", []):
                ink = stroke.get("ink")
                if ink:
                    ink["frames"] = [asset(f"annotation_ink/{event['annotation_id']}/{ink['dir']}/frame_{i:03d}.png") for i in range(ink["frame_count"])]
        props = {"fps":timeline["fps"], "width":timeline["canvas"][0], "height":timeline["canvas"][1], "total_duration_sec":timeline["slide_duration_sec"], "subtitle_style":subtitle_style or {}, "slides":[{"slide_id":timeline.get("slide_id","preview"), "start_sec":0, "duration_sec":timeline["slide_duration_sec"], "scene":scene, "audio_file":asset("voice.mp3"), "audio_timeline":prepared["audio_timeline"], "animation_timeline":prepared["animation_timeline"], "annotation_timeline":timeline}]}
        props_path = public / "props.json"
        props_path.write_text(json.dumps(props,ensure_ascii=False),encoding="utf-8")
        with _EXPORT_GATE:
            executable = bundle / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
            result = run_subprocess_killable(["node",str(executable),"render","src/index.tsx","ArticleVideo",str(output),f"--props={props_path}","--codec=h264","--concurrency=1"],cwd=str(bundle),timeout_sec=600,capture_output=True,text=True,encoding="utf-8",errors="replace")
        if result.returncode != 0 or not output.is_file():
            raise RuntimeError("预览视频导出失败：" + str(result.stderr)[-1000:])
        return token
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(public,ignore_errors=True)
