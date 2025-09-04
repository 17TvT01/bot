import threading
import datetime
from collections import deque
from typing import Deque, Dict, List, Optional


class ConversationMemory:
    """Lightweight conversation memory with optional persistence via ai_enhancements.

    - Keeps a rolling window of recent turns in-process for fast access.
    - Persists turns to ai_enhancements user_data['conversations'] when available.
    - Exposes provider-friendly history format.
    """

    def __init__(self, max_turns: int = 200) -> None:
        self._lock = threading.RLock()
        self._turns: Deque[Dict[str, str]] = deque(maxlen=max_turns)
        self._max_turns = max_turns
        self._enabled: bool = True

    def add_turn(self, role: str, content: str) -> None:
        if not self._enabled:
            return
        role = 'assistant' if role not in ('user', 'assistant') else role
        item = {
            'role': role,
            'content': content if isinstance(content, str) else str(content),
            'timestamp': datetime.datetime.now().isoformat()
        }
        with self._lock:
            self._turns.append(item)
        # Best-effort persist
        try:
            from .ai_enhancements import get_ai_assistant  # lazy import
            ai = get_ai_assistant()
            with ai._lock:  # type: ignore[attr-defined]
                conv = ai.user_data.get('conversations') or []
                if not isinstance(conv, list):
                    conv = []
                conv.append(item)
                ai.user_data['conversations'] = conv[-self._max_turns:]
                ai.needs_saving = True
        except Exception:
            pass

    def get_recent(self, n: int = 12) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._turns)[-max(1, int(n)) :]

    def get_provider_history(self, n: int = 8) -> List[Dict[str, str]]:
        """Return history in provider-friendly role/content pairs."""
        items = self.get_recent(n)
        return [{'role': it.get('role','user'), 'content': it.get('content','') or ''} for it in items]

    # --- Controls ---
    def enable(self) -> None:
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        with self._lock:
            self._enabled = False

    def is_enabled(self) -> bool:
        with self._lock:
            return bool(self._enabled)

    def clear(self) -> None:
        with self._lock:
            self._turns.clear()
        try:
            from .ai_enhancements import get_ai_assistant  # lazy import
            ai = get_ai_assistant()
            with ai._lock:  # type: ignore[attr-defined]
                ai.user_data['conversations'] = []
                ai.needs_saving = True
        except Exception:
            pass

    def peek(self, n: int = 3) -> List[Dict[str, str]]:
        return self.get_recent(n)


_memory_singleton: Optional[ConversationMemory] = None


def get_memory() -> ConversationMemory:
    global _memory_singleton
    if _memory_singleton is None:
        _memory_singleton = ConversationMemory()
    return _memory_singleton

# --- Feature glue: simple memory control via commands ---
import unicodedata

def _strip_diacritics(s: str) -> str:
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')
    except Exception:
        return s or ''

def _norm(s: str) -> str:
    s = (s or '').lower().strip()
    s = _strip_diacritics(s)
    return ' '.join(s.split())

keywords = ["ghi nho", "ngu canh", "bo nho", "history", "context"]
patterns = [
    "bat ghi nho", "tat ghi nho", "xoa lich su hoi thoai", "xoa ngu canh",
    "xem ngu canh gan day", "xem ngu canh", "clear history", "enable memory", "disable memory"
]

def main(command: str = None) -> str:
    cm = get_memory()
    text = _norm(command or '')
    if not text:
        return (
            "Dieu khien bo nho hoi thoai:\n"
            "- bat ghi nho | tat ghi nho\n"
            "- xoa lich su hoi thoai\n"
            "- xem ngu canh gan day"
        )
    if any(w in text for w in ["bat ghi nho", "enable memory", "bat bo nho"]):
        cm.enable()
        return "Da bat ghi nho hoi thoai."
    if any(w in text for w in ["tat ghi nho", "disable memory", "tat bo nho"]):
        cm.disable()
        return "Da tat ghi nho hoi thoai."
    if any(w in text for w in ["xoa lich su", "xoa ngu canh", "clear history", "xoa lich su hoi thoai"]):
        cm.clear()
        return "Da xoa lich su hoi thoai."
    if any(w in text for w in ["xem ngu canh", "ngu canh gan day", "xem ngu canh gan day", "show context"]):
        rows = cm.peek(3)
        if not rows:
            return "Chua co ngu canh."
        lines = []
        for r in rows:
            lines.append(f"- {r.get('role','user')}: {r.get('content','')[:80]}")
        return "Ngu canh gan day:\n" + "\n".join(lines)
    return "Khong nhan duoc lenh dieu khien bo nho. Thu: 'bat ghi nho' hoac 'xem ngu canh gan day'."
