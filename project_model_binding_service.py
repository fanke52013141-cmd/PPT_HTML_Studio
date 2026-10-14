"""HTML-only project overrides over existing connections and creation packages.

No secrets on disk or in public summaries. Submission snapshots are immutable
and process-local; interrupted jobs must be explicitly resubmitted.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path

from model_connection_service import bind_model_connection, resolve_model_connection
from pipeline_lifecycle import project_artifact_lock, write_json_atomic
from project_config_runtime import get_config_value, _api_key_from_secrets
from project_model_binding_models import ProjectModelBindingUpdate


class ModelBindingError(ValueError):
    pass


class ModelBindingConflict(ModelBindingError):
    pass


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _path(project):
    return Path(project.run_dir) / "planning/project_model_binding.json"


def _load(project):
    path = _path(project)
    if not path.exists():
        return {"schema_version": "0.1.0", "revision": 0, "bindings": {}}
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError()
        doc = json.loads(path.read_text(encoding="utf-8"))
        if (doc["schema_version"] not in {"0.1.0", "0.2.0"} or type(doc["revision"]) is not int
                or doc["revision"] < 0 or not isinstance(doc["bindings"], dict)
                or set(doc["bindings"]) - {"text", "image", "planning"}):
            raise ValueError()
        for item in doc["bindings"].values():
            if item["mode"] not in {"inherit", "fixed"}:
                raise ValueError()
            if item["mode"] == "fixed":
                _validate_snapshot(item["snapshot"])
        return doc
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise ModelBindingError("项目模型配置损坏或版本不支持，请修复配置") from exc


def _validate_snapshot(snapshot):
    from model_connection_service import _clean_endpoint, _clean_public_config
    keys = {"connection_id", "provider", "model", "endpoint", "credential_ref", "public_config"}
    if (not isinstance(snapshot, dict) or set(snapshot) != keys
            or not isinstance(snapshot["model"], str) or not snapshot["model"].strip()
            or not isinstance(snapshot["provider"], str) or not snapshot["provider"].strip()):
        raise ValueError("模型配置不完整")
    for name in ("connection_id", "endpoint", "credential_ref"):
        if snapshot[name] is not None and not isinstance(snapshot[name], str):
            raise ValueError("模型配置字段类型无效")
    _clean_endpoint(snapshot.get("endpoint"))
    _clean_public_config(snapshot.get("public_config", {}))


def _snapshot(connection, kind):
    if connection.kind != kind:
        raise ModelBindingError("模型连接类型与用途不一致")
    value = {key: getattr(connection, key) for key in (
        "connection_id", "provider", "model", "endpoint", "credential_ref", "public_config"
    )}
    _validate_snapshot(value)
    return json.loads(json.dumps(value))


def save_project_model_binding(project, request: ProjectModelBindingUpdate, *, binder=None):
    binder = binder or bind_model_connection
    with project_artifact_lock(project.run_dir):
        current = _load(project)
        if current["revision"] != request.expected_revision:
            raise ModelBindingConflict("模型配置已被修改，请刷新后重试；当前草稿尚未保存")
        bindings = {}
        for kind in ("text", "image", "planning"):
            selection = getattr(request, kind)
            if selection is None:
                if kind in current["bindings"]:
                    bindings[kind] = current["bindings"][kind]
                continue
            old = current["bindings"].get(kind, {})
            if selection.mode == "legacy":
                continue
            if selection.mode == "inherit":
                bindings[kind] = {"mode": "inherit"}
            elif (old.get("mode") == "fixed" and not selection.rebind
                  and old["snapshot"]["connection_id"] == selection.connection_id):
                bindings[kind] = old
            else:
                try:
                    snapshot = _snapshot(binder(selection.connection_id), "text" if kind == "planning" else kind)
                except Exception as exc:
                    raise ModelBindingError("所选模型连接不可用于新绑定，请检查类型和启用状态") from exc
                bindings[kind] = {"mode": "fixed", "snapshot": snapshot}
        changed = bindings != current["bindings"]
        if changed:
            current = {"schema_version": "0.2.0" if "planning" in bindings else current["schema_version"], "revision": current["revision"] + 1, "bindings": bindings}
            write_json_atomic(_path(project), current)
        return {"changed": changed, "revision": current["revision"]}


def _effective(project, kind, doc, resolver, setting):
    selected = doc["bindings"].get(kind)
    if selected and selected["mode"] == "fixed":
        return selected["snapshot"], "fixed"
    connection_id = setting("html_planning_connection_id" if kind == "planning" else "html_visual_connection_id") if kind in {"planning", "text"} else None
    if connection_id:
        try:
            return _snapshot(resolver(connection_id), "text"), "stage_default"
        except Exception as exc:
            raise ModelBindingError("HTML 阶段模型连接不可用，请检查配置") from exc
    if kind == "planning":
        return None, "text_fallback"
    if selected is None:
        name = "storyboard" if kind == "text" else "image_generation"
        reference = get_config_value(project, f"model_bindings.{name}")
        if reference is not None:
            try:
                return _snapshot(resolver(reference["connection_id"]), kind), "creation_config"
            except Exception as exc:
                raise ModelBindingError("创作包模型连接不可用，请检查配置") from exc
    prefix = "llm" if kind == "text" else "image"
    return {"connection_id": None, "provider": setting(f"{prefix}_provider") or "openai_compatible",
            "model": setting(f"{prefix}_model") or "", "endpoint": setting(f"{prefix}_base_url") or None,
            "credential_ref": None, "public_config": {}}, "global"


@dataclass(frozen=True)
class FrozenModel:
    provider: str
    model: str
    endpoint: str | None = field(repr=False)
    api_key: str = field(repr=False)
    source: str
    connection_id: str | None
    config_hash: str
    error: str = ""
    max_tokens: int | None = None
    reasoning_effort: str | None = None
    temperature: float | None = None
    supports_images: bool | None = None
    image_resolution: str | None = None
    image_quality: str | None = None

    def require_ready(self):
        if self.error:
            raise ModelBindingError(self.error)
        return self

    def summary(self):
        return {"source": self.source, "connection_id": self.connection_id,
                "provider": self.provider, "model": self.model, "config_hash": self.config_hash,
                "ready": not bool(self.error), "error": self.error,
                "parameters": {name: value for name in ("max_tokens", "reasoning_effort", "temperature", "supports_images", "image_resolution", "image_quality")
                               if (value := getattr(self, name)) is not None}}


@dataclass(frozen=True)
class FrozenProjectModels:
    revision: int
    text: FrozenModel
    image: FrozenModel
    planning: FrozenModel | None = None

    def summary(self):
        result = {"binding_revision": self.revision, "text": self.text.summary(), "image": self.image.summary()}
        if self.planning is not None and self.planning is not self.text:
            result["planning"] = self.planning.summary()
        return result


def freeze_project_models(project, *, required=("text",), resolver=None, credential=None, setting=None):
    if setting is None:
        from config_store import get_setting
        setting = get_setting
    if credential is None:
        from credential_store import get_credential
        credential = get_credential
    resolver = resolver or resolve_model_connection
    with project_artifact_lock(project.run_dir):
        doc = _load(project)
        models = {}
        for kind in ("text", "image", "planning"):
            snapshot, source = _effective(project, kind, doc, resolver, setting)
            if snapshot is None:
                models[kind] = models["text"]
                if kind in required:
                    models[kind].require_ready()
                continue
            error = ""
            key = ""
            try:
                _validate_snapshot(snapshot)
                if source == "global":
                    key = setting("llm_api_key" if kind == "text" else "image_api_key") or ""
                else:
                    key = _api_key_from_secrets(credential(snapshot["credential_ref"]))
                if not key:
                    raise ValueError()
            except Exception:
                error = f"{'图片' if kind == 'image' else '文字'}模型或凭据不可用，请检查模型配置"
            public = {k: v for k, v in snapshot.items() if k != "credential_ref"}
            max_tokens = None
            if kind != "image":
                from runtime_support import parse_int_setting
                value = (snapshot["public_config"].get("max_tokens", 12000)
                         if source != "global" else setting("llm_max_tokens") or 12000)
                max_tokens = parse_int_setting(value, 12000, 1024, 65536)
                public["effective_parameters"] = {"max_tokens": max_tokens}
            config = snapshot["public_config"]
            effort = config.get("reasoning_effort")
            temperature = config.get("temperature")
            supports_images = config.get("supports_images")
            image_resolution = str(config.get("resolution") or config.get("toapis_resolution") or "").upper() or None if kind == "image" else None
            image_quality = str(config.get("quality") or config.get("toapis_quality") or "").lower() or None if kind == "image" else None
            if image_resolution not in (None, "1K", "2K", "4K") or image_quality not in (None, "auto", "low", "medium", "high", "xhigh", "max"):
                raise ModelBindingError("图片分辨率或质量参数无效")
            if effort not in (None, "low", "high", "max") or (temperature is not None and (type(temperature) not in (float, int) or not 0 <= temperature <= 2)) or (supports_images is not None and type(supports_images) is not bool):
                raise ModelBindingError("模型请求参数无效")
            if any(value is not None for value in (effort, temperature, supports_images)):
                public["request_parameters"] = {"reasoning_effort": effort, "temperature": temperature, "supports_images": supports_images}
            models[kind] = FrozenModel(snapshot["provider"], snapshot["model"], snapshot["endpoint"],
                                       key, source, snapshot["connection_id"], _hash(public), error, max_tokens, effort, temperature, supports_images, image_resolution, image_quality)
            if kind in required:
                models[kind].require_ready()
        return FrozenProjectModels(doc["revision"], **models)


def get_project_model_binding(project, **kwargs):
    with project_artifact_lock(project.run_dir):
        frozen = freeze_project_models(project, required=(), **kwargs)
        doc = _load(project)
        effective = frozen.summary()
        effective.setdefault("planning", (frozen.planning or frozen.text).summary())
        return {"revision": doc["revision"], "effective": effective, "bindings": {
            kind: {"mode": doc["bindings"].get(kind, {}).get("mode", "legacy"),
                   "connection_id": getattr(frozen, kind).connection_id}
            for kind in ("text", "image", "planning")}}
