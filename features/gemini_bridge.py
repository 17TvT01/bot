import os
import json
from typing import List, Optional, Dict, Any

# Environment variable for the API key
API_KEY_ENV = "GEMINI_API_KEY"

def _config_path() -> str:
    # Store config in the root directory
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(root, "assistant_config.json")

def load_config() -> Dict[str, Any]:
    try:
        path = _config_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}

def save_config(cfg: Dict[str, Any]) -> None:
    try:
        path = _config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_saved_api_key() -> str:
    return str(load_config().get(API_KEY_ENV, ""))

def is_configured() -> bool:
    """Return True if a Gemini API key is configured."""
    key = os.environ.get(API_KEY_ENV, "").strip() or get_saved_api_key().strip()
    return bool(key)

def set_api_key(api_key: str) -> None:
    """Update and persist the Gemini API key."""
    cfg = load_config()
    cfg[API_KEY_ENV] = api_key.strip()
    os.environ[API_KEY_ENV] = api_key.strip()
    save_config(cfg)

def _http_post(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    """POST helper using requests or urllib."""
    try:
        import requests
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        try:
            import urllib.request
            import urllib.error
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except Exception as e:
            return {"error": {"message": str(e)}}

def ask_gemini(
    user_text: str,
    *,
    history: Optional[List[Dict[str, str]]] = None,
    model: str = "gemini-1.5-flash",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: float = 30.0,
) -> str:
    """Query the Google Gemini API."""
    api_key = os.environ.get(API_KEY_ENV, "").strip() or get_saved_api_key().strip()
    if not api_key:
        return "Chưa cấu hình GEMINI_API_KEY. Hãy đặt biến môi trường để bật Gemini."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Gemini uses a different format for history
    contents = []
    if history:
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": item["content"]}]})
    
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    data = _http_post(url, headers, payload, timeout=timeout)

    if not isinstance(data, dict):
        return "Không nhận được phản hồi hợp lệ từ Gemini."

    if "error" in data:
        msg = data.get("error", {}).get("message") or str(data.get("error"))
        return f"Lỗi khi gọi Gemini: {msg}"

    try:
        candidates = data.get("candidates") or []
        if not candidates:
            # Check for safety ratings block
            prompt_feedback = data.get("promptFeedback")
            if prompt_feedback and prompt_feedback.get("blockReason"):
                return f"Yêu cầu bị chặn bởi Gemini vì lý do: {prompt_feedback.get('blockReason')}"
            return "Gemini không có phản hồi."
        
        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "" # No text parts
        
        return parts[0].get("text", "").strip()

    except (KeyError, IndexError, TypeError) as e:
        return f"Không phân tích được phản hồi từ Gemini: {str(e)}"

# Feature glue
keywords = ["gemini", "ask gemini", "set gemini key"]
patterns = ["hỏi gemini", "ask gemini", "set gemini key to"]

def main(command: Optional[str] = None) -> str:
    """Entry point for manual Gemini queries and configuration."""
    text = (command or "").strip()
    
    # Command to set the API key
    if text.lower().startswith("set gemini key to"):
        key = text[len("set gemini key to"):].strip()
        if key:
            set_api_key(key)
            return "Đã lưu API key cho Gemini."
        else:
            return "Vui lòng cung cấp API key."

    # Fallback to asking Gemini
    if not is_configured():
        return "Chưa cấu hình Gemini. Hãy dùng lệnh 'set gemini key to YOUR_KEY' hoặc đặt biến môi trường GEMINI_API_KEY."

    if not text:
        return "Bạn muốn hỏi Gemini điều gì?"

    return ask_gemini(text)
