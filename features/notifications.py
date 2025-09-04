import threading
from typing import Callable, Dict, List

_listeners: List[Callable[[Dict], None]] = []
_lock = threading.Lock()

def register(listener: Callable[[Dict], None]) -> None:
    with _lock:
        if listener not in _listeners:
            _listeners.append(listener)

def unregister(listener: Callable[[Dict], None]) -> None:
    with _lock:
        try:
            _listeners.remove(listener)
        except ValueError:
            pass

def notify(event: Dict) -> None:
    """Broadcast a notification event to all listeners.

    Event example for reminders:
      { 'type': 'reminder', 'id': '123', 'title': 'Họp', 'description': '...', 'time': '2025-01-01T09:00:00' }
    """
    with _lock:
        listeners = list(_listeners)
    for cb in listeners:
        try:
            cb(event)
        except Exception:
            pass

