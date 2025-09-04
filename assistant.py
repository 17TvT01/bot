import os
import re
import importlib
import datetime
import threading
import concurrent.futures
from functools import lru_cache
from typing import Dict, Callable, List, Tuple, Optional, Any
import unicodedata
import time
import sys

# Lazy loading for heavy libraries
_word_tokenize = None
_word_tokenize_lock = threading.Lock()

def get_word_tokenize():
    global _word_tokenize
    if _word_tokenize is None:
        with _word_tokenize_lock:
            if _word_tokenize is None:
                try:
                    from underthesea import word_tokenize as wt
                    _word_tokenize = wt
                except ImportError:
                    _word_tokenize = lambda text: text.lower().split()
    return _word_tokenize

_fuzz = None
_fuzz_lock = threading.Lock()

def get_fuzz():
    global _fuzz
    if _fuzz is None:
        with _fuzz_lock:
            if _fuzz is None:
                try:
                    from fuzzywuzzy import fuzz as fz
                    _fuzz = fz
                except ImportError:
                    _fuzz = type('obj', (object,), {
                        'token_set_ratio': lambda a, b: 0,
                        'partial_ratio': lambda a, b: 0
                    })
    return _fuzz

# --- OPTIMIZED FEATURE LOADING ---

# Global feature registry with thread-safe access
features: Dict[str, Tuple[Callable, List[str], List[str]]] = {}
feature_loading_lock = threading.Lock()
features_loaded = threading.Event()
basic_features_loaded = False  # Flag để đánh dấu khi tính năng cơ bản đã được tải

# Thread pool for feature execution
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _debug(msg: str):
    """Print debug messages safely without crashing on encoding issues."""
    try:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        try:
            sys.stdout.write(str(msg) + "\n")
        except UnicodeEncodeError:
            sys.stdout.write(str(msg).encode(enc, errors="replace").decode(enc, errors="replace") + "\n")
    except Exception:
        try:
            print(str(msg))
        except Exception:
            pass

def _safe_display(text: str) -> str:
    """Return text safe for display without mojibake: strip diacritics and non-ASCII control chars."""
    try:
        t = text if isinstance(text, str) else str(text)
        # Remove combining marks (accents)
        t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
        # Remove non-printable / non-ASCII (keep common whitespace)
        import re as _re
        t = _re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", t)
        # Normalize whitespace
        t = _re.sub(r"\s+", " ", t).strip()
        return t
    except Exception:
        try:
            return (text or "").encode('ascii', errors='ignore').decode('ascii', errors='ignore')
        except Exception:
            return ""

def load_features_async():
    """Load features in a background thread at startup with optimized loading."""
    def _load_features():
        global basic_features_loaded
        try:
            features_dir = os.path.join(os.path.dirname(__file__), "features")
            feature_files = []
            
            essential_features = ["calculator.py", "system_info.py"]
            important_features = ["weather.py", "reminder.py", "nlp_processor.py", "chitchat.py", "app_launcher.py"]
            supplementary_features = ["ai_enhancements.py", "work_assistant.py", "gemini_bridge.py"]
            
            # Collect all feature files with priority ordering
            for filename in os.listdir(features_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    # Phân loại tính năng theo mức độ ưu tiên
                    if filename in essential_features:
                        priority = 0  # Tải ngay lập tức
                    elif filename in important_features:
                        priority = 1  # Tải sau tính năng thiết yếu
                    elif filename in supplementary_features:
                        priority = 2  # Tải sau các tính năng quan trọng
                    else:
                        priority = 3  # Tải cuối cùng
                    feature_files.append((priority, filename))
            
            # Sort by priority (highest first)
            feature_files.sort(key=lambda x: x[0])
            feature_files = [f[1] for f in feature_files]
            
            # Tải các tính năng thiết yếu trước
            essential_batch = [f for f in feature_files if f in essential_features]
            if essential_batch:
                print("Loading essential features...")
                _load_feature_batch(essential_batch, features_dir)
                # Đánh dấu là đã tải các tính năng cơ bản
                basic_features_loaded = True
            
            # Sau đó tải các tính năng quan trọng
            important_batch = [f for f in feature_files if f in important_features]
            if important_batch:
                print("Loading important features...")
                _load_feature_batch(important_batch, features_dir)
            
            # Cuối cùng tải các tính năng bổ sung
            remaining_files = [f for f in feature_files if f not in essential_features and f not in important_features]
            for i in range(0, len(remaining_files), 2):  # Tải 2 tính năng bổ sung mỗi lần
                batch = remaining_files[i:i + 2]
                print(f"Loading supplementary features: {batch}")
                _load_feature_batch(batch, features_dir)
                
        except Exception as e:
            print(f"Error loading features: {e}")
        finally:
            # Đảm bảo đánh dấu là đã tải xong ngay cả khi có lỗi
            if not features_loaded.is_set():
                features_loaded.set()
    
    # Start feature loading in background thread
    loading_thread = threading.Thread(target=_load_features, daemon=True)
    loading_thread.start()
    return loading_thread

def _load_feature_batch(filenames: List[str], features_dir: str):
    """Load a batch of features with error handling."""
    for filename in filenames:
        module_name = filename[:-3]
        try:
            module = importlib.import_module(f"features.{module_name}")

            # Find the appropriate function with priority
            function = None
            # Prefer explicit module-level handler names first, then getters
            function_names = [
                module_name,
                "main",
                "handle",
                f"get_{module_name}"
            ]
            
            for func_name in function_names:
                if hasattr(module, func_name):
                    func = getattr(module, func_name)
                    if callable(func):
                        function = func
                        break

            if function:
                # Get keywords and patterns with defaults
                keywords = getattr(module, "keywords", [])
                patterns = getattr(module, "patterns", [])
                
                with feature_loading_lock:
                    features[module_name] = (function, keywords, patterns)
                    
        except Exception as e:
            # Log error but continue loading other features
            print(f"Failed to load feature {module_name}: {e}")

def get_greeting() -> str:
    """Returns a greeting message."""
    return "Chào bạn, tôi có thể giúp gì cho bạn?"

def get_time(*args) -> str:
    """Returns the current time."""
    now = datetime.datetime.now()
    return f"Bây giờ là {now.hour}:{now.minute}"

def open_notepad(*args) -> str:
    """Opens Notepad application."""
    try:
        if os.name == 'nt':
            os.startfile("notepad.exe")
        else:
            return "Chức năng này chỉ hỗ trợ Windows."
        return "Đã mở ứng dụng ghi chú."
    except Exception as e:
        return f"Lỗi khi mở ứng dụng: {e}"

def open_application(app_name: str) -> str:
    """Opens a specified application."""
    # Dictionary mapping Vietnamese app names to actual executable names
    app_mapping = {
        "calculator": "calc.exe",
        "máy tính": "calc.exe",
        "tính toán": "calc.exe",
        "paint": "mspaint.exe",
        "vẽ": "mspaint.exe",
        "wordpad": "write.exe",
        "soạn thảo": "write.exe",
        "chrome": "chrome.exe",
        "trình duyệt": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "excel": "excel.exe",
        "word": "winword.exe",
        "powerpoint": "powerpnt.exe",
        "notepad": "notepad.exe",
        "ghi chú": "notepad.exe"
    }
    
    # Get the actual executable name (whitelist only)
    executable_name = app_mapping.get(app_name.lower())
    if not executable_name:
        return "Ứng dụng chưa nằm trong danh sách an toàn. Thử: notepad, calc, paint, chrome, edge, word, excel, powerpoint."
    
    try:
        if os.name == 'nt':
            os.startfile(executable_name)
            return f"Đã mở ứng dụng {app_name}."
        else:
            return "Chức năng này chỉ hỗ trợ Windows."
    except Exception as e:
        return f"Lỗi khi mở ứng dụng {app_name}: {e}"

def show_help(command: Optional[str] = None) -> str:
    """Trả về danh sách chức năng và ví dụ sử dụng."""
    try:
        lines = []
        lines.append("Mình có thể giúp bạn với các chức năng sau:")

        # Luôn sẵn sàng (cơ bản)
        lines.append("- Thời gian: hỏi giờ hiện tại. Ví dụ: 'mấy giờ rồi?'")
        lines.append("- Tính toán: cộng/trừ/nhân/chia. Ví dụ: 'tính 5 cộng 3'")
        lines.append("- Mở ứng dụng: notepad, chrome,... Ví dụ: 'mở notepad'")

        # Theo các tính năng đã/đang tải
        with feature_loading_lock:
            available = set(features.keys())
        if "weather" in available:
            lines.append("- Thời tiết: 'thời tiết Hà Nội', 'nhiệt độ Sài Gòn'")
        if "system_info" in available:
            lines.append("- Thông tin hệ thống: 'thông tin hệ thống'")
        if "reminder" in available:
            lines.append("- Nhắc việc: 'nhắc tôi uống nước sau 10 phút'")
        if "app_launcher" in available:
            lines.append("- Khởi chạy ứng dụng hệ thống khác")
        if "chitchat" in available:
            lines.append("- Trò chuyện: 'kể chuyện cười', 'chào'…")
        if "nlp_processor" in available or "work_assistant" in available:
            lines.append("- Xử lý ngôn ngữ/Trợ lý công việc: hỏi/tra cứu đơn giản")

        lines.append("- Trợ giúp: 'trợ giúp', 'bạn có thể làm gì', 'giới thiệu chức năng'")

        if not available:
            lines.append("(Một số tính năng đang được tải nền; bạn có thể dùng các chức năng cơ bản ngay bây giờ.)")

        return "\n".join(lines)
    except Exception as e:
        return f"Không thể lấy danh sách chức năng: {e}"

# Pre-load basic built-in features for faster response
basic_features = {
    "time": (get_time, ["giờ", "thời gian"], []),
    "notepad": (open_notepad, ["notepad", "ghi", "chú"], []),
    "application": (open_application, ["mở", "khởi động", "chạy"], [])
}

# Initialize with basic features for immediate response
features.update(basic_features)

@lru_cache(maxsize=1024)  # Increased cache size for better performance
def preprocess_text(text: str) -> List[str]:
    """
    Preprocesses text using word tokenization with optimized caching.
    """
    tokenize = get_word_tokenize()
    return tokenize(text.lower())

def _strip_diacritics(s: str) -> str:
    """Remove Vietnamese diacritics for accent-insensitive matching."""
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')
    except Exception:
        return (s or '').lower()

def _normalize_for_match(s: str) -> str:
    """Lowercase, strip diacritics and collapse whitespace for robust keyword checks."""
    s = (s or '').lower()
    s = _strip_diacritics(s)
    try:
        import re as _re
        s = _re.sub(r"\s+", " ", s).strip()
    except Exception:
        s = s.strip()
    return s

# Pre-cache common commands for faster response
_common_commands_cache = {}
def _precache_common_commands():
    """Pre-cache processing for common commands."""
    common_commands = [
        "mấy giờ rồi", "thời gian", "giờ", 
        "mở notepad", "mở ghi chú",
        "thời tiết", "nhiệt độ", "hệ thống",
        "tính toán", "cộng", "trừ", "nhân", "chia"
    ]
    for cmd in common_commands:
        _common_commands_cache[cmd] = preprocess_text(cmd)

# Cache for feature matching results
_feature_match_cache = {}
_feature_match_cache_lock = threading.Lock()

def find_best_feature(command: str, tokens: List[str]) -> Tuple[Optional[Callable], float, str]:
    """
    Optimized feature matching with priority-based lookup.
    """
    # Check if features are loaded, wait briefly if not
    if not features_loaded.is_set():
        # Wait max 100ms for features to load
        features_loaded.wait(timeout=0.1)

    with feature_loading_lock:
        current_features = features.copy()

    # Fast-path cache for repeated lookups to reduce matching latency
    try:
        cache_key = ("/".join(tokens) or _normalize_for_match(command)) + f"|{len(current_features)}"
        with _feature_match_cache_lock:
            cached = _feature_match_cache.get(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    # Normalized text for robust matching (accent-insensitive, whitespace-collapsed)
    norm_cmd = _normalize_for_match(command)

    # Early: provider triggers (explicit user intent)
    try:
        from features.gemini_bridge import is_configured as _gm_conf  # type: ignore
    except Exception:
        _gm_conf = lambda: False  # type: ignore
    try:
        from features.chatgpt_bridge import is_configured as _cg_conf  # type: ignore
    except Exception:
        _cg_conf = lambda: False  # type: ignore

    if ("gemini" in norm_cmd or "hoi gemini" in norm_cmd or "h?i gemini" in norm_cmd) and "gemini_bridge" in current_features and _gm_conf():
        return (current_features["gemini_bridge"][0], 1.0, command)
    if ("chatgpt" in norm_cmd or "hoi chatgpt" in norm_cmd or "h?i chatgpt" in norm_cmd) and "chatgpt_bridge" in current_features and _cg_conf():
        return (current_features["chatgpt_bridge"][0], 1.0, command)

    # Early: normalized help detection
    _help_norm = [
        "ban co the lam gi",
        "ban co chuc nang gi",
        "gioi thieu chuc nang",
        "tro giup",
        "huong dan",
        "help"
    ]
    if any(p in norm_cmd for p in _help_norm):
        return (show_help, 1.0, command)

    # Early: time queries (avoid misrouting "mấy giờ" as app launch due to diacritics)
    _time_norm = ["may gio", "gio", "thoi gian"]
    if any(w in norm_cmd for w in _time_norm):
        return (get_time, 1.0, "")

    # Early: normalized app-launch intent to prefer app_launcher
    if "app_launcher" in current_features:
        _launch_norm = ["may", "mo", "chay", "khoi dong", "khoi", "open", "launch", "run", "ung dung", "app"]
        if any(w in norm_cmd for w in _launch_norm):
            return (current_features["app_launcher"][0], 1.0, command)

    # Early: route general questions.
    # First let NLP handle; only escalate to providers if NLP is unavailable or later deemed insufficient
    q_words = ["la gi", "la ai", "o dau", "bao nhieu", "the nao", "tai sao", "khi nao", "ai la"]
    if ("?" in command) or any(q in norm_cmd for q in q_words):
        if "nlp_processor" in current_features:
            return (current_features["nlp_processor"][0], 1.0, command)
        # If NLP not available, fall back to preferred/provider later

    # Help/intro phrases (substring match; robust to tokenization)
    help_phrases = [
        "bạn có thể làm gì",
        "bạn có chức năng gì",
        "giới thiệu chức năng",
        "trợ giúp",
        "hướng dẫn",
        "help"
    ]
    if any(p in command.lower() for p in help_phrases):
        return (show_help, 1.0, command)

    # Tier 1: Fast keyword matching for built-in commands
    if any(word in tokens for word in ["giờ", "thời gian"]):
        return (get_time, 1.0, "")
    if any(word in tokens for word in ["notepad", "ghi", "chú"]):
        return (open_notepad, 1.0, "")
    if any(word in tokens for word in ["mở", "khởi động", "chạy"]):
        for keyword in ["mở", "khởi động", "chạy"]:
            if keyword in tokens:
                keyword_index = tokens.index(keyword)
                app_name = " ".join(tokens[keyword_index + 1:])
                return (open_application, 1.0, app_name)
    
    # Prefer dedicated app launcher when user intends to open an app
    launch_words = [
        "mở", "mo", "chạy", "chay", "khởi", "khoi", "khởi động", "khoi dong",
        "open", "launch", "run", "ứng", "ung", "dụng", "dung", "app"
    ]
    if "app_launcher" in current_features and any(w in tokens for w in launch_words):
        return (current_features["app_launcher"][0], 1.0, command)

    # Tier 2: Feature-specific matching
    # Reminder feature (events/notes) — prioritize before generic 'thong tin'
    if "reminder" in current_features:
        reminder_words = ["nh��_c", "nh��_c nh��Y", "l��<ch", "s��� ki���n", "h��1n", "reminder", "calendar", "ghi chA�", "ghi chu", "su kien"]
        if any(w in tokens for w in reminder_words):
            return (current_features["reminder"][0], 1.0, command)
        try:
            norm_cmd2 = _normalize_for_match(command)
            if any(p in norm_cmd2 for p in ["su kien", "ghi chu", "lich", "nhac nho", "calendar", "event"]):
                return (current_features["reminder"][0], 1.0, command)
        except Exception:
            pass
    # System info feature
    if "system_info" in current_features and any(word in tokens for word in ["hệ thống", "thông tin", "máy tính", "system"]):
        return (current_features["system_info"][0], 1.0, "")
    
    # Weather feature
    if "weather" in current_features and any(word in tokens for word in ["thời tiết", "weather", "nhiệt độ", "độ ẩm", "dự báo"]):
        return (current_features["weather"][0], 1.0, command)
        
    # Reminder feature
    if "reminder" in current_features and any(word in tokens for word in ["nhắc", "nhắc nhở", "lịch", "sự kiện", "hẹn", "reminder", "calendar"]):
        return (current_features["reminder"][0], 1.0, command)
        
    # NLP Processor feature
    if "nlp_processor" in current_features and any(word in tokens for word in ["hiểu", "phân tích", "ngôn ngữ", "nlp", "xử lý", "lời nói", "cảm xúc", "ý định", "xóa", "hủy", "delete", "remove"]):
        return (current_features["nlp_processor"][0], 1.0, command)

    # Calculator feature with optimized matching
    if "calculator" in current_features:
        calc_func, _, _ = current_features["calculator"]
        has_nums = bool(re.search(r'\d', command))
        has_math_op = any(op in tokens for op in ["cộng", "trừ", "nhân", "chia", "tính", "+", "-", "*", "/"])
        if has_nums and has_math_op:
            return (calc_func, 1.0, command)

    # Tier 3: Fuzzy matching fallback with optimized scoring
    best_score = 0.7  # Higher threshold for better accuracy
    best_feature = None
    
    for feature_name, (func, keywords, patterns) in current_features.items():
        if feature_name in ["calculator", "system_info", "weather"]:
            continue  # Already handled above

        # Combine all matching phrases
        all_phrases = keywords + patterns
        if not all_phrases:
            continue

        # Optimized scoring: check if any keyword matches exactly first
        exact_match = any(keyword in tokens for keyword in keywords if keyword)
        if exact_match:
            return (func, 1.0, command)

        # Fallback to fuzzy matching
        score = get_fuzz().token_set_ratio(command.lower(), " ".join(all_phrases)) / 100.0
        
        if score > best_score:
            best_score = score
            best_feature = func

    if best_feature:
        _ret = (best_feature, best_score, command)
        try:
            with _feature_match_cache_lock:
                _feature_match_cache[cache_key] = _ret
        except Exception:
            pass
        return _ret

    return (None, 0, "")

def run_feature_async(command: str, callback: Callable[[str], None]):
    """
    Run feature asynchronously with callback for GUI integration.
    Enhanced with AI capabilities.
    """
    def _process_command():
        try:
            print(f"DEBUG: Processing command: '{command}'")
            tokens = preprocess_text(command)

            # Record user turn into conversation memory
            try:
                from features.memory import get_memory  # type: ignore
                get_memory().add_turn('user', command)
            except Exception:
                pass

            # --- Simple teach-and-reply feature ---
            try:
                taught_path = os.path.join(os.path.dirname(__file__), 'taught.json')
                import json as _json
                taught = {}
                if os.path.exists(taught_path):
                    try:
                        with open(taught_path, 'r', encoding='utf-8', errors='replace') as f:
                            data = _json.load(f)
                        if isinstance(data, dict):
                            taught = {str(k): str(v) for k, v in data.items()}
                    except Exception:
                        taught = {}

                # Teach syntax: "day: <pattern> => <reply>" or "teach: ... => ..."
                try:
                    teach_pat = re.compile(r"^(day|teach)\s*[:\-]?\s*(.+?)\s*(=>|->|:)\s*(.+)$", re.IGNORECASE)
                    m = teach_pat.match(_strip_diacritics(command))
                    if m:
                        key = _normalize_for_match(m.group(2))
                        val = m.group(4).strip()
                        if key and val:
                            taught[key] = val
                            try:
                                with open(taught_path, 'w', encoding='utf-8') as f:
                                    _json.dump(taught, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                            result = f"Da hoc: khi thay '{key}' se tra loi: '{val}'"
                            callback(result)
                            return
                except Exception:
                    pass

                # If a taught pattern matches, answer immediately
                try:
                    norm_cmd_quick = _normalize_for_match(command)
                    for k, v in taught.items():
                        if k and k in norm_cmd_quick:
                            callback(v)
                            return
                except Exception:
                    pass
            except Exception:
                pass
            feature, confidence, params = find_best_feature(command, tokens)
            
            if feature:
                print(f"DEBUG: Found feature: {getattr(feature, '__name__', 'unknown')} with confidence {confidence}")
                # If NLP feature selected, inject external context into NLP processor
                try:
                    with feature_loading_lock:
                        _map = features.copy()
                    chosen_name = None
                    for _name, (_func, _, _) in _map.items():
                        if _func is feature:
                            chosen_name = _name
                            break
                    if chosen_name == 'nlp_processor':
                        try:
                            from features.memory import get_memory  # type: ignore
                            from features.nlp_processor import set_nlp_context_window  # type: ignore
                            hist = get_memory().get_provider_history(8)
                            set_nlp_context_window(hist)
                        except Exception:
                            pass
                except Exception:
                    pass
                result = feature(params)
                # Ensure result is a string for downstream processing and logging
                if not isinstance(result, str):
                    try:
                        result = str(result)
                    except Exception:
                        result = ""
                print(f"DEBUG: Feature result: {result}")
                # If NLP handled but returned low-value output, escalate to provider
                try:
                    with feature_loading_lock:
                        current_features = features.copy()
                    selected_name = None
                    for name, (func, _, _) in current_features.items():
                        if func is feature:
                            selected_name = name
                            break
                    def _should_escalate(cmd: str, res: str) -> bool:
                        try:
                            if not isinstance(res, str):
                                return True
                            r = res.strip().lower()
                            if not r:
                                return True
                            bad_starts = ["xin loi", "xin li", "khong the", "khong tim", "khong hieu", "da phan tich"]
                            if any(r.startswith(p) for p in bad_starts):
                                return True
                            # Heuristic: if result contains only meta like "Y dinh:" without content
                            if r.startswith("y dinh:") and ("|" in r or len(r) < 40):
                                return True
                            return False
                        except Exception:
                            return False
                    # Inject panel markers for GUI if applicable
                    try:
                        if selected_name == 'system_info':
                            result = f"[[PANEL:SYSTEM_INFO]]{result}"
                        elif getattr(feature, '__name__', '') == 'get_time':
                            result = f"[[PANEL:CLOCK]]{result}"
                        elif selected_name == 'reminder':
                            result = f"[[PANEL:NOTES]]{result}"
                    except Exception:
                        pass

                    if selected_name == 'nlp_processor' and _should_escalate(command, result):
                        # Ask via preferred provider
                        def _provider_answer(cmd: str) -> Optional[str]:
                            try:
                                from features.provider_prefs import get_default_provider  # type: ignore
                                preferred = get_default_provider()
                            except Exception:
                                preferred = None
                            # Safe gemini symbols
                            try:
                                from features.gemini_bridge import ask_gemini, is_configured as is_gemini_configured  # type: ignore
                            except Exception:
                                ask_gemini = None  # type: ignore
                                def is_gemini_configured(): return False  # type: ignore
                            # Try preferred first
                            if preferred == 'chatgpt':
                                try:
                                    from features.chatgpt_bridge import ask_chatgpt, is_configured as is_cg  # type: ignore
                                    if is_cg():
                                        return ask_chatgpt(cmd)
                                except Exception:
                                    pass
                            if preferred == 'gemini' and ask_gemini and is_gemini_configured():
                                try:
                                    return ask_gemini(cmd)
                                except Exception:
                                    pass
                            # Otherwise try any configured
                            try:
                                from features.chatgpt_bridge import ask_chatgpt, is_configured as is_cg  # type: ignore
                                if is_cg():
                                    return ask_chatgpt(cmd)
                            except Exception:
                                pass
                            if ask_gemini and is_gemini_configured():
                                try:
                                    return ask_gemini(cmd)
                                except Exception:
                                    pass
                            return None
                        alt = _provider_answer(command)
                        if isinstance(alt, str) and alt.strip():
                            result = alt
                except Exception:
                    pass
                # Enhance with AI if available
                try:
                    from features.ai_enhancements import enhance_with_ai
                    result = enhance_with_ai(result, command, True)
                except ImportError:
                    pass  # AI features not available
                # Return early for handled feature to avoid running global fallback block
                try:
                    callback(result)
                finally:
                    return
            else:
                # Fallback path when no feature matched
                # Safe defaults for provider symbols
                ask_gemini = None
                def is_gemini_configured():  # type: ignore
                    return False
                try:
                    from features.gemini_bridge import ask_gemini as _ask_gemini, is_configured as _is_gemini_configured  # type: ignore
                    ask_gemini = _ask_gemini
                    is_gemini_configured = _is_gemini_configured  # type: ignore
                except Exception:
                    pass
            # Use preferred provider for fallback when nothing matched
            try:
                from features.provider_prefs import get_default_provider  # type: ignore
                preferred = get_default_provider()
            except Exception:
                preferred = None
            used = False
            if preferred == "chatgpt":
                try:
                    from features.chatgpt_bridge import ask_chatgpt, is_configured as is_cg  # type: ignore
                    if is_cg():
                        print("DEBUG: No feature found. Falling back to ChatGPT (preferred).")
                        try:
                            from features.memory import get_memory  # type: ignore
                            hist = get_memory().get_provider_history(8)
                        except Exception:
                            hist = None
                        result = ask_chatgpt(command, history=hist)
                        used = True
                except Exception:
                    pass
            elif preferred == "gemini":
                try:
                    if is_gemini_configured():
                        print("DEBUG: No feature found. Falling back to Gemini (preferred).")
                        try:
                            from features.memory import get_memory  # type: ignore
                            hist = get_memory().get_provider_history(8)
                        except Exception:
                            hist = None
                        result = ask_gemini(command, history=hist)
                        used = True
                except Exception:
                    pass
            if not used:
                if is_gemini_configured():
                    print("DEBUG: No feature found. Falling back to Gemini.")
                    try:
                        from features.memory import get_memory  # type: ignore
                        hist = get_memory().get_provider_history(8)
                    except Exception:
                        hist = None
                    result = ask_gemini(command, history=hist)
                else:
                    try:
                        from features.chatgpt_bridge import ask_chatgpt, is_configured as is_cg  # type: ignore
                        if is_cg():
                            print("DEBUG: No feature found. Falling back to ChatGPT.")
                            try:
                                from features.memory import get_memory  # type: ignore
                                hist = get_memory().get_provider_history(8)
                            except Exception:
                                hist = None
                            result = ask_chatgpt(command, history=hist)
                            used = True
                    except Exception:
                        pass
                    else:
                        # Original fallback logic
                        suggestions = []
                        with feature_loading_lock:
                            for _, (_, keywords, patterns) in features.items():
                                for pattern in patterns:
                                    if get_fuzz().partial_ratio(command, pattern) > 60:
                                        suggestions.append(pattern)
                                        break
                        
                        if suggestions:
                            suggestion_text = "\n".join(f"- {s}" for s in suggestions[:3])
                            result = f"Xin lỗi, tôi không hiểu. Có phải bạn muốn nói:\n{suggestion_text}"
                        else:
                            result = "Xin lỗi, tôi không hiểu yêu cầu của bạn. Hãy thử diễn đạt theo cách khác."
                # except ImportError:
                    # Fallback if gemini_bridge doesn't exist
                    result = "Xin lỗi, tôi không hiểu yêu cầu của bạn. Hãy thử diễn đạt theo cách khác."

                # Enhance error response with AI
                try:
                    from features.ai_enhancements import enhance_with_ai
                    result = enhance_with_ai(result, command, False)
                except ImportError:
                    pass
            
            # Đảm bảo callback được gọi trong luồng chính của GUI
            try:
                prev = result
                result = result if isinstance(result, str) else str(result)
                safe = result
                try:
                    safe = _safe_display(result)
                except Exception:
                    pass
                _debug(f"DEBUG: Calling callback with result: {safe[:50]}..." if len(safe) > 50 else f"DEBUG: Calling callback with result: {safe}")
            except Exception:
                pass
            # Record assistant turn into conversation memory
            try:
                from features.memory import get_memory  # type: ignore
                get_memory().add_turn('assistant', result if isinstance(result, str) else str(result))
            except Exception:
                pass
            callback(result)
        except Exception as e:
            error_msg = f"Có lỗi xảy ra: {str(e)}"
            # Record failed command for AI learning
            try:
                from features.ai_enhancements import enhance_with_ai
                error_msg = enhance_with_ai(error_msg, command, False)
            except ImportError:
                pass
            _debug(f"DEBUG: About to call callback with error: {error_msg}")
            callback(error_msg)
            _debug("DEBUG: Callback finished.")
    
    # Submit to thread pool and ensure callback runs in main thread
    def _safe_process():
        try:
            _process_command()
        except Exception as e:
            print(f"ERROR in _safe_process: {e}")
            # Đảm bảo callback vẫn được gọi ngay cả khi có lỗi
            callback(f"Có lỗi xảy ra: {str(e)}")
            print("DEBUG: Error callback called from _safe_process")
    
    executor.submit(_safe_process)

def run_feature(command: str) -> str:
    """
    Synchronous version for backward compatibility.
    """
    result_event = threading.Event()
    result_container = [None]
    
    def _callback(result):
        result_container[0] = result
        result_event.set()
    
    run_feature_async(command, _callback)
    result_event.wait(timeout=10.0)  # 10 second timeout
    
    return result_container[0] if result_container[0] is not None else "Timeout: Không thể xử lý yêu cầu"

def initialize_assistant():
    """Initializes the assistant without blocking the UI thread.

    - Starts feature loading in a background thread.
    - Runs precache of common commands in a separate daemon thread to avoid
      heavy NLP imports (e.g., underthesea) from blocking the GUI startup.
    """
    # Start loading features first (non-blocking)
    load_features_async()

    # Run precache in background so any heavy imports don't block the UI
    threading.Thread(target=_precache_common_commands, daemon=True).start()
