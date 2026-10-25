"""Task-local HTTP accounting hook; no global client monkey-patching."""
from contextlib import contextmanager
from contextvars import ContextVar

_OBSERVER=ContextVar('html_json_request_observer',default=None)

@contextmanager
def observe_json_requests(callback):
    token=_OBSERVER.set(callback)
    try:yield
    finally:_OBSERVER.reset(token)

def notify(state,**facts):
    callback=_OBSERVER.get()
    if callback:callback(state,**facts)
