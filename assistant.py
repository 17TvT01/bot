import os
import re
import importlib
import datetime
import threading
import concurrent.futures
from functools import lru_cache
from typing import Dict, Callable, List, Tuple, Optional, Any
import time

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

def load_features_async():
    """Load features in a background thread at startup with optimized loading."""
    def _load_features():
        global basic_features_loaded
        try:
            features_dir = os.path.join(os.path.dirname(__file__), "features")
            feature_files = []
            
            essential_features = ["calculator.py", "system_info.py"]
            important_features = ["weather.py", "reminder.py", "nlp_processor.py", "chitchat.py", "app_launcher.py"]
            supplementary_features = ["ai_enhancements.py", "work_assistant.py"]
            
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
                features_loaded.set()
            
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
            function_names = [
                f"get_{module_name}",
                module_name,
                "main",
                "handle"
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
    
    # Get the actual executable name from mapping, or use the input as is
    executable_name = app_mapping.get(app_name.lower(), app_name)
    
    try:
        if os.name == 'nt':
            os.startfile(executable_name)
            return f"Đã mở ứng dụng {app_name}."
        else:
            return "Chức năng này chỉ hỗ trợ Windows."
    except Exception as e:
        return f"Lỗi khi mở ứng dụng {app_name}: {e}"

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
        return (best_feature, best_score, command)

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
            feature, confidence, params = find_best_feature(command, tokens)
            
            if feature:
                print(f"DEBUG: Found feature: {getattr(feature, '__name__', 'unknown')} with confidence {confidence}")
                result = feature(params)
                print(f"DEBUG: Feature result: {result}")
                # Enhance with AI if available
                try:
                    from features.ai_enhancements import enhance_with_ai
                    result = enhance_with_ai(result, command, True)
                except ImportError:
                    pass  # AI features not available
            else:
                # Generate suggestions
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
                
                # Enhance error response with AI
                try:
                    from features.ai_enhancements import enhance_with_ai
                    result = enhance_with_ai(result, command, False)
                except ImportError:
                    pass
            
            # Đảm bảo callback được gọi trong luồng chính của GUI
            print(f"DEBUG: Calling callback with result: {result[:50]}..." if len(result) > 50 else f"DEBUG: Calling callback with result: {result}")
            callback(result)
        except Exception as e:
            error_msg = f"Có lỗi xảy ra: {str(e)}"
            # Record failed command for AI learning
            try:
                from features.ai_enhancements import enhance_with_ai
                error_msg = enhance_with_ai(error_msg, command, False)
            except ImportError:
                pass
            print(f"DEBUG: About to call callback with error: {error_msg}")
            callback(error_msg)
            print("DEBUG: Callback finished.")
    
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
    """Initializes the assistant's features in the background."""
    _precache_common_commands()
    load_features_async()
