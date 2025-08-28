import platform
import time
from functools import lru_cache

# Lazy loading for psutil
psutil = None

def _load_psutil():
    """Lazy load psutil module when needed"""
    global psutil
    if psutil is None:
        import psutil as psutil_module
        psutil = psutil_module

# Keywords and patterns for feature detection
keywords = ["thông tin", "system", "hệ thống", "máy tính", "cấu hình"]
patterns = [
    "thông tin hệ thống",
    "thông tin máy tính",
    "cấu hình hệ thống",
    "cấu hình máy tính",
    "system info"
]

# Cache system information for 5 seconds
@lru_cache(maxsize=1)
def get_cached_system_info() -> dict:
    """Get cached system information"""
    # Đảm bảo psutil được tải khi cần
    _load_psutil()
    
    return {
        "timestamp": time.time(),
        "os_info": {
            "Hệ điều hành": platform.system(),
            "Phiên bản": platform.version(),
            "Kiến trúc": platform.machine(),
        },
        "cpu_info": {
            "Bộ xử lý": platform.processor(),
            "Số lõi vật lý": psutil.cpu_count(logical=False),
            "Tổng số lõi": psutil.cpu_count(logical=True),
            "Tần số CPU tối đa": f"{psutil.cpu_freq().max:.2f}Mhz",
            "Tần số CPU tối thiểu": f"{psutil.cpu_freq().min:.2f}Mhz",
            "Tần số CPU hiện tại": f"{psutil.cpu_freq().current:.2f}Mhz",
            "Mức sử dụng CPU": f"{psutil.cpu_percent(interval=None)}%",
        },
        "memory": psutil.virtual_memory()
    }

def system_info(command: str = None) -> str:
    """
    Lấy thông tin chi tiết về hệ thống.
    """
    try:
        # Đảm bảo psutil được tải khi cần
        _load_psutil()
        
        # Get cached system information
        cached_info = get_cached_system_info()
        memory = cached_info["memory"]
        
        system_details = {
            "Hệ điều hành": cached_info["os_info"],
            "CPU": cached_info["cpu_info"],
            "Bộ nhớ": {
                "Tổng bộ nhớ": f"{memory.total / (1024**3):.2f} GB",
                "Bộ nhớ khả dụng": f"{memory.available / (1024**3):.2f} GB",
                "Bộ nhớ đã dùng": f"{memory.used / (1024**3):.2f} GB",
                "Phần trăm sử dụng": f"{memory.percent}%",
            }
        }

        # Format the output string
        output = "Thông tin hệ thống:\n"
        for category, details in system_details.items():
            output += f"\n--- {category} ---\n"
            for key, value in details.items():
                output += f"{key}: {value}\n"
        return output

    except Exception as e:
        return f"Đã xảy ra lỗi khi lấy thông tin hệ thống: {e}"
