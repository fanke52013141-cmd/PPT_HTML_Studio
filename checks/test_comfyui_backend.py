from __future__ import annotations

from typing import Any

import comfyui_backend as backend


class _Response:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _Client:
    def __init__(self, object_info: dict[str, Any]) -> None:
        self.object_info = object_info

    def __enter__(self) -> "_Client":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def get(self, path: str) -> _Response:
        if path == "/system_stats":
            return _Response(200, {"system": "ok"})
        if path == "/object_info":
            return _Response(200, self.object_info)
        raise AssertionError(path)


def _workflow() -> dict[str, dict[str, Any]]:
    return {
        "1": {"class_type": "BSAI_IndexTTS2.5Loader", "inputs": {}},
        "2": {"class_type": "BSAI_IndexTTS2.5Synthesis", "inputs": {"text": ""}},
        "3": {"class_type": "BSAI_IndexTTS2.5SaveAudio", "inputs": {}},
    }


def test_inspect_tts_preflight_reports_success(monkeypatch) -> None:
    workflow = _workflow()
    monkeypatch.setattr(
        backend,
        "_make_client",
        lambda **_kwargs: _Client(
            {
                "BSAI_IndexTTS2.5Loader": {},
                "BSAI_IndexTTS2.5Synthesis": {},
                "BSAI_IndexTTS2.5SaveAudio": {},
            }
        ),
    )

    result = backend.inspect_tts_preflight(workflow)

    assert result["success"] is True
    assert result["service_reachable"] is True
    assert result["missing_nodes"] == []
    assert result["errors"] == []


def test_inspect_tts_preflight_reports_missing_nodes(monkeypatch) -> None:
    monkeypatch.setattr(
        backend,
        "_make_client",
        lambda **_kwargs: _Client({"BSAI_IndexTTS2.5Synthesis": {}}),
    )

    result = backend.inspect_tts_preflight(_workflow())

    assert result["success"] is False
    assert result["missing_nodes"] == [
        "BSAI_IndexTTS2.5Loader",
        "BSAI_IndexTTS2.5SaveAudio",
    ]
    assert any("缺少工作流节点" in error for error in result["errors"])


def test_inspect_tts_preflight_does_not_call_service_for_invalid_workflow(
    monkeypatch,
) -> None:
    called = False

    def fail_client(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("invalid workflow must fail before network probe")

    monkeypatch.setattr(backend, "_make_client", fail_client)

    result = backend.inspect_tts_preflight({"1": {"inputs": {}}})

    assert result["success"] is False
    assert called is False
    assert "工作流不是 ComfyUI API 格式" in result["errors"]


def test_inspect_tts_preflight_maps_offline_service(monkeypatch) -> None:
    def fail_client(**_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(backend, "_make_client", fail_client)

    result = backend.inspect_tts_preflight(_workflow())

    assert result["success"] is False
    assert result["service_reachable"] is False
    assert any("ComfyUI 连接失败" in error for error in result["errors"])


# ---------------------------------------------------------------------------
# 客户端生命周期回归：共享单例 + 调用方 with 的并发踩踏
#
# 历史缺陷：_make_client 返回模块级单例，而全部调用方用 ``with`` 包裹——
# 一个操作退出时会把仍在使用中的共享连接池 close 掉，另一个并发任务/
# 健康检查随即抛 "Cannot send a request on a closed client"。修复后
# _make_client 每次返回独占的新客户端。
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    """记录生命周期与构造参数的 httpx.Client 替身。

    子类通过 ``registry`` 类属性收集实例（类体不参与闭包作用域，
    因此在类创建后显式绑定）。
    """

    registry: list = []

    def __init__(self, *, base_url, timeout, trust_env, limits, **_extra):
        self.base_url = base_url
        self.timeout = timeout
        self.trust_env = trust_env
        self.limits = limits
        self.closed = False
        self.registry.append(self)

    def close(self) -> None:
        self.closed = True


def test_make_client_creates_independent_clients(monkeypatch) -> None:
    class TrackingClient(_FakeHttpxClient):
        pass

    created: list[_FakeHttpxClient] = []
    TrackingClient.registry = created

    monkeypatch.setattr(backend.httpx, "Client", TrackingClient)

    first = backend._make_client(timeout=5.0)
    second = backend._make_client(timeout=30.0)

    assert first is not second, "_make_client must return a fresh exclusive client per call"
    assert first.base_url == second.base_url
    assert first.timeout is not second.timeout, "per-call timeout must not be shared"
    first.close()
    assert first.closed is True
    assert second.closed is False, "closing one client must not close another"


def test_health_check_failure_closes_its_own_client(monkeypatch) -> None:
    class FailingClient(_FakeHttpxClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True
            return None

        def get(self, _path):
            raise OSError("connection refused")

    created: list[_FakeHttpxClient] = []
    FailingClient.registry = created
    monkeypatch.setattr(backend.httpx, "Client", FailingClient)

    assert backend.check_health() is False
    assert created, "health check must construct exactly one client per call"
    assert all(client.closed for client in created), "failed health check must still close its client"


def test_concurrent_health_check_and_tasks_never_share_a_client(monkeypatch) -> None:
    """真实本地 HTTP 服务上并发跑健康检查与两个假任务。

    修复前（单例 + with）：任一 ``with`` 退出都会关闭共享实例，另一并发
    使用者立即抛 "Cannot send a request on a closed client"/误报离线。
    """
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler API)
            body = b'{"system": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("PPT_COMFYUI_URL", f"http://127.0.0.1:{server.server_address[1]}")

        errors: list[Exception] = []
        health_results: list[bool] = []

        def fake_task() -> None:
            try:
                with backend._make_client(timeout=10.0) as client:
                    for _ in range(25):
                        response = client.get("/system_stats")
                        if response.status_code != 200:
                            raise RuntimeError(f"unexpected status {response.status_code}")
                        time.sleep(0.004)
            except Exception as exc:  # noqa: BLE001 - 收集全部并发失败
                errors.append(exc)

        def health_loop() -> None:
            try:
                for _ in range(40):
                    if not backend.check_health():
                        errors.append(RuntimeError("health check falsely reported offline"))
                    time.sleep(0.002)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        workers = [threading.Thread(target=fake_task) for _ in range(2)]
        workers.append(threading.Thread(target=health_loop))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        assert errors == [], f"concurrent use must not close clients in flight: {errors[:3]}"
        assert len(health_results) == 0 or all(health_results)
    finally:
        server.shutdown()
        server.server_close()
