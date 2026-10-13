"""Target-specific local HTML preflight. No server/database/provider imports."""
from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from scripts.media_tools import resolve_media_tool

TARGETS = ("static_html", "generate_existing", "generate_new_images", "snapshot_pptx", "video")


def inspect_html_preflight(target, *, repo_root=None, run_dir=None, scene=None,
                           output_dir=None, model_readiness=None, min_free_bytes=64 * 1024 * 1024,
                           probe=None):
    """Readiness flags come from the host's resolved configuration, never keys.

    This probes prerequisites; it does not grant visual/audio approval or prove
    a provider connection. Existing export gates remain authoritative.
    """
    if target not in TARGETS:
        raise ValueError("Unsupported HTML preflight target")
    if type(min_free_bytes) is not int or min_free_bytes < 0:
        raise ValueError("min_free_bytes must be a nonnegative integer")
    if scene is not None and not isinstance(scene, dict):
        raise ValueError("scene must be an object")
    if model_readiness is not None and (not isinstance(model_readiness, dict)
        or set(model_readiness) - {"text", "image"}
        or any(type(v) is not bool for v in model_readiness.values())):
        raise ValueError("Only boolean model readiness is accepted")
    root = Path(repo_root or Path(__file__).parent).resolve()
    checks = []

    def check(code, passed, message):
        checks.append({"code": code, "passed": bool(passed), "message": message})

    visual = root / "html_engine/visual"
    required = [visual / "preview/player.js", visual / "generated/catalog.json",
                visual / "schema.json", root / "html_engine/tools/preflight-browser.cjs"]
    check("RUNTIME_FILES", all(p.is_file() for p in required), "HTML 运行文件需完整；从源构建缺失产物")
    font = "Microsoft YaHei"
    try:
        theme_id = (scene or {}).get("themeRef", {}).get("id", "neutral-baseline")
        if not isinstance(theme_id, str) or not theme_id or any(not (c.isalnum() or c in "_-") for c in theme_id):
            raise ValueError()
        theme = json.loads((visual / "themes" / f"{theme_id}.json").read_text(encoding="utf-8"))
        font = theme["font"]["family"]
        check("THEME", isinstance(font, str) and bool(font), "使用注册主题中声明的实际字体")
    except (OSError, ValueError, KeyError, TypeError):
        check("THEME", False, "主题缺失或不可解析，请检查注册主题")

    destination = Path(output_dir).resolve() if output_dir else Path(tempfile.gettempdir())
    try:
        if not destination.is_dir():
            raise OSError()
        with tempfile.TemporaryFile(dir=destination) as f:
            f.write(b"hps-preflight")
            f.flush()
        free = shutil.disk_usage(destination).free
        check("OUTPUT_WRITABLE", True, "输出目录可创建临时文件")
        check("DISK_SPACE", free >= min_free_bytes, "可用空间需满足请求预算；此最低值不估计整片大小")
    except OSError:
        check("OUTPUT_WRITABLE", False, "输出目录需已存在且可写")

    configured = model_readiness or {}
    if target.startswith("generate_"):
        check("TEXT_MODEL_CONFIGURED", configured.get("text") is True, "需文字模型配置就绪；未测试供应商连接")
    if target in ("generate_existing", "generate_new_images"):
        check("IMAGE_MODEL_CONFIGURED", configured.get("image") is True, "完整设计参考需生图配置就绪；复用主体也不跳过设计，未发收费请求")

    node = shutil.which("node")
    check("NODE", bool(node), "需要 Node.js 执行共享渲染器")
    browser = {}
    if node and all(p.is_file() for p in required):
        try:
            if probe:
                browser = probe({"font_family": font, "scene": scene})
            else:
                with tempfile.TemporaryDirectory(prefix="hps-preflight-") as temp:
                    spec = Path(temp) / "request.json"
                    spec.write_text(json.dumps({"font_family": font, "scene": scene}, ensure_ascii=False), encoding="utf-8")
                    env = dict(os.environ)
                    env.pop("HPS_HTML_RESOURCES", None)
                    env.pop("HPS_CANDIDATE_DIAGNOSTIC", None)
                    if run_dir:
                        resources = Path(run_dir).resolve() / "planning/html_visual/resources.json"
                        if resources.is_file():
                            env["HPS_HTML_RESOURCES"] = str(resources)
                    result = subprocess.run([node, str(required[-1]), str(spec)], cwd=root,
                                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=45)
                    browser = json.loads(result.stdout)
            check("BROWSER", browser.get("browser") is True, "实际浏览器启动失败时安装 Chromium 或配置 HPS_CHROME")
            check("FONT", browser.get("font") is True, "主题字体必须实际加载；缺失时安装字体或选择兼容主题")
            if scene is not None:
                check("SCENE_RENDER", browser.get("scene_passed") is True, "现有场景需通过共享渲染器与资源检查")
        except (OSError, ValueError, subprocess.TimeoutExpired):
            check("BROWSER", False, "浏览器检查失败或超时；检查本机依赖与字体")

    if target in ("snapshot_pptx", "video"):
        check("SCENE_REQUIRED", scene is not None, "输出任务需提供要检查的实际 scene")
    if target == "snapshot_pptx":
        check("PPTX_LIBRARY", importlib.util.find_spec("pptx") is not None, "快照 PPTX 需要现有 python-pptx 依赖")
    if target == "video":
        from tts_artifacts import confirmation_status
        from html_creation_workflow import _validate_slide_binding
        if run_dir and scene and isinstance(scene.get("id"), str):
            try:
                contract = json.loads((Path(run_dir) / "planning/visual_contract.json").read_text(encoding="utf-8"))
                slide_ids = [s["slide_id"] for s in contract["slides"]]
                check("STORYBOARD_SCOPE", scene["id"] in slide_ids, "当前场景需属于实际分镜页面集合")
                confirmed = scene["id"] in slide_ids and confirmation_status(run_dir, slide_ids).get("confirmed", False)
                check("AUDIO_CONFIRMED", confirmed, "需当前音频确认及文件指纹；不能用作者时钟替代")
                check("AUDIO_BINDING", not _validate_slide_binding(Path(run_dir), scene["id"]), "需有效动作/语块绑定和时间轴")
            except (OSError, ValueError, KeyError, TypeError):
                check("AUDIO_CONFIRMED", False, "无法核验当前音频或绑定")
        else:
            check("AUDIO_CONFIRMED", False, "视频检查需项目运行目录与实际场景")
        for name in ("ffmpeg", "ffprobe"):
            tool = resolve_media_tool(name, root)
            ok = False
            if tool:
                try:
                    result = subprocess.run([tool, "-version"], capture_output=True, timeout=10)
                    ok = result.returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    pass
            check(name.upper(), ok, f"需可执行的 {name}，使用共享媒体工具定位")

    return {"format": "hps.html.preflight", "version": "0.1.0", "target": target,
            "ready": all(c["passed"] for c in checks), "checks": checks,
            "browser_executable": browser.get("executable"),
            "provider_connection_tested": False, "approval_granted": False,
            "scope": "local_prerequisites_only"}
