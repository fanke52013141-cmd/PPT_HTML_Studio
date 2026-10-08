"""Process-local cooperative stop signals; persistent jobs retain terminal state.

Stopping is checked only at safe boundaries. It never claims to abort an
upstream HTTP request or a subprocess that is already running.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
import threading
import uuid
import inspect
from typing import Callable


KINDS = frozenset({"storyboard_script", "storyboard_visual", "mask", "tts", "video"})


class GenerationStopped(RuntimeError):
    pass


class GenerationAlreadyRunning(RuntimeError):
    pass


@dataclass
class _Control:
    operation_id: str
    stop: threading.Event = field(default_factory=threading.Event)
    on_stop: Callable[[], None] | None = None


_lock = threading.Lock()
_active: dict[tuple[str, str], _Control] = {}


def reserve(project_id: str, kind: str, operation_id: str | None = None) -> str:
    if kind not in KINDS:
        raise ValueError("不支持的任务类型")
    with _lock:
        key = (project_id, kind)
        if key in _active:
            raise GenerationAlreadyRunning("该项目已有同类任务，请等待完成或请求停止")
        control = _Control(operation_id or uuid.uuid4().hex)
        _active[key] = control
        return control.operation_id


def finish(project_id: str, kind: str, operation_id: str) -> None:
    with _lock:
        key = (project_id, kind)
        if _active.get(key) and _active[key].operation_id == operation_id:
            del _active[key]


def status(project_id: str, kind: str) -> dict:
    if kind not in KINDS:
        raise ValueError("不支持的任务类型")
    with _lock:
        control = _active.get((project_id, kind))
        return {"active": control is not None,
                "operation_id": control.operation_id if control else None,
                "stop_requested": bool(control and control.stop.is_set())}


def request_stop(project_id: str, kind: str, operation_id: str) -> dict:
    if kind not in KINDS:
        raise ValueError("不支持的任务类型")
    with _lock:
        control = _active.get((project_id, kind))
        accepted = bool(control and control.operation_id == operation_id)
        if accepted:
            control.stop.set()
        handler = control.on_stop if accepted else None
        if handler:
            control.on_stop = None
    if handler:
        handler()
    return {"accepted": accepted, "operation_id": operation_id,
            "message": "已请求停止，当前请求或阶段安全完成后停止" if accepted else "该任务已经结束或发生变化"}


def bind_stop_handler(project_id: str, kind: str, operation_id: str, handler: Callable[[], None]) -> None:
    with _lock:
        control = _active.get((project_id, kind))
        if not control or control.operation_id != operation_id:
            return
        already_requested = control.stop.is_set()
        if not already_requested:
            control.on_stop = handler
    if already_requested:
        handler()


def stop_requested(project_id: str, kind: str) -> bool:
    with _lock:
        control = _active.get((project_id, kind))
        return bool(control and control.stop.is_set())


def checkpoint(project_id: str, kind: str) -> None:
    if stop_requested(project_id, kind):
        raise GenerationStopped("已按用户请求停止；已完成的产物保留")


@contextmanager
def operation(project_id: str, kind: str, operation_id: str | None = None):
    identity = operation_id or reserve(project_id, kind)
    try:
        checkpoint(project_id, kind)
        yield identity
    finally:
        finish(project_id, kind, identity)


def controlled(kind: str, *, method: bool = False):
    def decorate(function):
        signature = inspect.signature(function)
        project_parameter = tuple(signature.parameters)[1 if method else 0]
        @wraps(function)
        def execute(*args, **kwargs):
            subject = signature.bind(*args, **kwargs).arguments[project_parameter]
            project_id = str(getattr(subject, "id", subject))
            try:
                with operation(project_id, kind):
                    return function(*args, **kwargs)
            except GenerationStopped as error:
                return {"success": False, "cancelled": True, "message": str(error)}
            except GenerationAlreadyRunning as error:
                return {"success": False, "busy": True, "message": str(error)}
        return execute
    return decorate
