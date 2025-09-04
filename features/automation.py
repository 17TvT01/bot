import re
import time
from typing import List

def _split_steps(cmd: str) -> List[str]:
    """Split a multi-step command by common Vietnamese separators."""
    if not cmd:
        return []
    text = cmd.strip()
    # Remove leading markers like 'tự động:', 'automation:'
    text = re.sub(r"^(tự\s+động|tu dong|automation|chuỗi|chuoi)\s*[:\-]?\s*", "", text, flags=re.IGNORECASE)
    # Split by separators: ';', '->', ',', 'rồi', 'sau đó'
    parts = re.split(r";|->|,|\brồi\b|\bsau đó\b", text, flags=re.IGNORECASE)
    steps = [p.strip() for p in parts if p and p.strip()]
    return steps

def automation(command: str = None) -> str:
    if not command:
        return "Dùng: 'tự động: <bước 1>; <bước 2>; ...' Ví dụ: 'tự động: xem nhắc nhở; mở bảng ghi chú'"
    try:
        steps = _split_steps(command)
        if not steps:
            return "Không tìm thấy bước nào để chạy."
        # Lazy import to avoid cycles
        import assistant as _assistant
        results = []
        for i, step in enumerate(steps, 1):
            try:
                res = _assistant.run_feature(step)
            except Exception as e:
                res = f"Lỗi ở bước {i}: {e}"
            results.append(f"[{i}] {step} -> {res}")
            time.sleep(0.05)
        return "\n".join(results)
    except Exception as e:
        return f"Không thể chạy chuỗi: {e}"

# Router metadata
keywords = ["tự động", "automation", "chuỗi", "multi-step", "workflow"]
patterns = [r"^tự\s+động", r"^automation", r"^chuỗi\b"]

