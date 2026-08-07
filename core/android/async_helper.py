"""
Async helper for running bridge calls from sync skill context
Uses a persistent background event loop that owns the websocket connections.
"""

import asyncio
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar('T')

# Background event loop thread
_bg_loop: asyncio.AbstractEventLoop = None
_bg_thread: threading.Thread = None
_bg_ready = threading.Event()

def _run_bg_loop(loop: asyncio.AbstractEventLoop):
    """Run event loop in background thread."""
    global _bg_loop
    _bg_loop = loop
    asyncio.set_event_loop(loop)
    _bg_ready.set()
    loop.run_forever()

def _ensure_bg_loop():
    """Ensure background event loop is running."""
    global _bg_thread, _bg_loop
    if _bg_thread is None or not _bg_thread.is_alive():
        _bg_ready.clear()
        loop = asyncio.new_event_loop()
        _bg_thread = threading.Thread(target=_run_bg_loop, args=(loop,), daemon=True)
        _bg_thread.start()
        _bg_ready.wait(timeout=5)

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine from sync context using background event loop.
    The background loop owns all websocket connections.
    """
    _ensure_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _bg_loop)
    return future.result(timeout=30)

def get_bg_loop() -> asyncio.AbstractEventLoop:
    """Get the background event loop."""
    _ensure_bg_loop()
    return _bg_loop

def shutdown_bg_loop():
    """Shutdown background event loop."""
    global _bg_loop, _bg_thread
    if _bg_loop and _bg_loop.is_running():
        _bg_loop.call_soon_threadsafe(_bg_loop.stop)
    if _bg_thread:
        _bg_thread.join(timeout=2)