"""Simple global cancellation registry used by actions to observe a global
"stop all" request initiated from the UI.

Usage:
    from cancel_registry import set_all, is_all_set
    if is_all_set():
        # respect cancellation
"""
import threading

_global_ev = threading.Event()


def set_all() -> None:
    _global_ev.set()


def clear_all() -> None:
    _global_ev.clear()


def is_all_set() -> bool:
    return _global_ev.is_set()
