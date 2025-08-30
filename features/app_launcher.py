import os
import shutil
import threading
from typing import Dict, List, Tuple, Optional
import re
import unicodedata

# Robust app launcher that can find and open apps by name.

_index_lock = threading.Lock()
_app_index: Dict[str, str] = {}
_indexed = False


def _strip_diacritics(s: str) -> str:
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    except Exception:
        return s


def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_key(s: str) -> str:
    s = _normalize(s)
    return _strip_diacritics(s)


def _start_menu_dirs() -> List[str]:
    paths = []
    programdata = os.environ.get('ProgramData')
    appdata = os.environ.get('APPDATA')
    if programdata:
        paths.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"))
    if appdata:
        paths.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
    return [p for p in paths if p and os.path.isdir(p)]


def _safe_walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        yield dirpath, filenames


def _build_index_if_needed():
    global _indexed
    if _indexed:
        return
    with _index_lock:
        if _indexed:
            return
        # Index Start Menu shortcuts and a few common locations
        for d in _start_menu_dirs():
            for dirpath, filenames in _safe_walk(d):
                for name in filenames:
                    if not name.lower().endswith((".lnk", ".appref-ms", ".url", ".exe")):
                        continue
                    path = os.path.join(dirpath, name)
                    key = _norm_key(os.path.splitext(name)[0])
                    _app_index[key] = path

        # Common direct executables from PATH (names only; resolution later with which)
        common_bins = [
            'chrome', 'msedge', 'firefox', 'notepad', 'calc', 'mspaint', 'write',
            'winword', 'excel', 'powerpnt', 'code', 'teams', 'skype', 'spotify',
            'zalo', 'telegram', 'discord', 'steam', 'obs64', 'vlc'
        ]
        for bn in common_bins:
            _app_index.setdefault(_norm_key(bn), bn)

        _indexed = True


_synonyms: Dict[str, str] = {
    # Vietnamese → canonical
    'trinh duyet': 'chrome',
    'trình duyệt': 'chrome',
    'may tinh': 'calc',
    'máy tính': 'calc',
    'soan thao': 'write',
    'soạn thảo': 'write',
    'anh': 'mspaint',
    've': 'mspaint',
    'ghi chu': 'notepad',
    'ghi chú': 'notepad',
    'word': 'winword',
    'excel': 'excel',
    'powerpoint': 'powerpnt',
    'photoshop': 'photoshop',
    'zalo': 'zalo',
    'telegram': 'telegram',
    'discord': 'discord',
    'spotify': 'spotify',
    'teams': 'teams',
    'skype': 'skype',
    'steam': 'steam',
    'vscode': 'code',
    'visual studio code': 'code',
}


def _extract_app_query(command: str) -> str:
    txt = _norm_key(command)
    # Remove common verbs/phrases around launching
    for w in [
        'mo ', 'mở ', 'khoi dong ', 'khởi động ', 'chay ', 'chạy ',
        'open ', 'launch ', 'run ', 'ung dung ', 'ứng dụng ', 'app '
    ]:
        if txt.startswith(w):
            txt = txt[len(w):]
    # Remove leading filler words
    txt = re.sub(r'^(giup |giúp |hay |hãy )', '', txt)
    return txt.strip()


def _resolve_candidate_paths(query: str) -> List[Tuple[str, str]]:
    """Return list of (display, path_or_bin) candidates best matching the query."""
    _build_index_if_needed()
    q = _norm_key(query)
    # Synonym mapping
    mapped = _synonyms.get(q, q)

    results: List[Tuple[str, str]] = []
    # 1) Exact key match
    if mapped in _app_index:
        results.append((mapped, _app_index[mapped]))

    # 2) Contains match over index keys
    for k, p in _app_index.items():
        if q and (q in k or k in q):
            results.append((k, p))

    # 3) If nothing, try PATH resolution directly
    if not results:
        which = shutil.which(mapped)
        if which:
            results.append((mapped, which))

    # Deduplicate by path
    seen = set()
    uniq: List[Tuple[str, str]] = []
    for name, path in results:
        key = os.path.normcase(path)
        if key not in seen:
            seen.add(key)
            uniq.append((name, path))
    return uniq


def _launch(path_or_bin: str) -> bool:
    try:
        if os.name != 'nt':
            return False
        # If it's a bare bin name, try PATH
        if os.path.sep not in path_or_bin and not os.path.exists(path_or_bin):
            full = shutil.which(path_or_bin)
            if full:
                os.startfile(full)
                return True
        # Otherwise start directly (works for .exe, .lnk, .appref-ms, .url)
        os.startfile(path_or_bin)
        return True
    except Exception:
        return False


def app_launcher(command: str = None) -> str:
    """Find and open an application by name. Supports Vietnamese with/without dấu."""
    if not command:
        return "Bạn muốn mở ứng dụng nào? Ví dụ: 'mở Chrome', 'mở máy tính', 'mở Zalo'"

    q = _extract_app_query(command)
    if not q:
        return "Bạn muốn mở ứng dụng nào?"

    cands = _resolve_candidate_paths(q)
    if not cands:
        # Offer top suggestions from index
        all_names = sorted(list(_app_index.keys()))[:8] if _app_index else []
        if all_names:
            suggestions = ", ".join(all_names[:5])
            return f"Không tìm thấy ứng dụng '{q}'. Bạn có muốn thử: {suggestions}"
        return f"Không tìm thấy ứng dụng '{q}'. Hãy thử tên khác hoặc dạng: 'mở Chrome'"

    # Try first few candidates
    for name, path in cands[:3]:
        if _launch(path):
            return f"Đã mở ứng dụng: {name}"

    # If all launches failed, present choices
    choices = "; ".join(p for _, p in cands[:5])
    return f"Tìm thấy nhưng không mở được tự động. Các đường dẫn: {choices}"


# Keywords and patterns to help the router recognize this feature
keywords = [
    'mở', 'mo', 'chạy', 'chay', 'khởi động', 'khoi dong', 'open', 'launch', 'run',
    'ứng dụng', 'ung dung', 'app'
]
patterns = [
    'mở ...', 'mo ...', 'chạy ...', 'khởi động ...', 'open ...', 'launch ...', 'run ...',
    'mở chrome', 'mở máy tính', 'mở notepad', 'mở zalo', 'mở telegram', 'mở spotify'
]

