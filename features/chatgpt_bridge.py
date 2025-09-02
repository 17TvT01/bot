import os
import json
import time
from typing import List, Optional, Dict, Any


API_KEY_ENV = "OPENAI_API_KEY"
API_BASE_ENV = "OPENAI_API_BASE"
MODEL_ENV = "OPENAI_MODEL"


def _config_path() -> str:
    # Store alongside the app root (parent of features)
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


def get_saved_model() -> str:
    return str(load_config().get(MODEL_ENV, "gpt-4o-mini"))


def get_saved_base() -> str:
    return str(load_config().get(API_BASE_ENV, "https://api.openai.com"))


def is_configured() -> bool:
    """Return True if an API key is configured via env or saved config."""
    key = os.environ.get(API_KEY_ENV, "").strip() or get_saved_api_key().strip()
    return bool(key)


def set_api_config(api_key: Optional[str] = None, *, model: Optional[str] = None, base: Optional[str] = None) -> None:
    """Update and persist API settings; also apply to current process env."""
    cfg = load_config()
    if api_key is not None:
        cfg[API_KEY_ENV] = api_key.strip()
        os.environ[API_KEY_ENV] = api_key.strip()
    if model is not None:
        cfg[MODEL_ENV] = model.strip()
        os.environ[MODEL_ENV] = model.strip()
    if base is not None:
        basev = base.strip().rstrip('/') or "https://api.openai.com"
        cfg[API_BASE_ENV] = basev
        os.environ[API_BASE_ENV] = basev
    save_config(cfg)


def _http_post(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    """POST helper that prefers 'requests' but falls back to urllib."""
    try:
        import requests  # type: ignore
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        # Fallback to urllib
        try:
            import urllib.request
            import urllib.error
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - user controls key, not URL
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except Exception as e:  # Return a structured error so caller can handle gracefully
            return {"error": {"message": str(e)}}


def _default_system_prompt(user_text: str) -> str:
    # Keep it short, Vietnamese-first but mirror user language if not Vietnamese
    return (
        "Bạn là trợ lý AI thân thiện. Trả lời ngắn gọn, đúng trọng tâm, "
        "ưu tiên tiếng Việt. Nếu người dùng dùng ngôn ngữ khác, hãy trả lời bằng ngôn ngữ đó."
    )


def ask_chatgpt(
    user_text: str,
    *,
    system_prompt: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 600,
    timeout: float = 30.0,
) -> str:
    """Query the OpenAI Chat Completions API and return the assistant message text.

    Configuration via env:
    - OPENAI_API_KEY: required
    - OPENAI_API_BASE: optional, default https://api.openai.com
    - OPENAI_MODEL: optional, default gpt-4o-mini
    """
    # Prefer env var, fallback to saved config
    api_key = os.environ.get(API_KEY_ENV, "").strip() or get_saved_api_key().strip()
    if not api_key:
        return "Chưa cấu hình OPENAI_API_KEY. Hãy đặt biến môi trường OPENAI_API_KEY để bật ChatGPT."

    base = (os.environ.get(API_BASE_ENV) or get_saved_base() or "https://api.openai.com").rstrip("/")
    mdl = (model or os.environ.get(MODEL_ENV) or get_saved_model() or "gpt-4o-mini").strip()
    url = f"{base}/v1/chat/completions"

    sys_prompt = system_prompt or _default_system_prompt(user_text)
    messages: List[Dict[str, str]] = [{"role": "system", "content": sys_prompt}]
    if history:
        # Include up to last 8 turns to keep things light
        messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_text})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": mdl,
        "messages": messages,
        "temperature": max(0.0, min(2.0, float(temperature))),
        "max_tokens": int(max_tokens),
    }

    data = _http_post(url, headers, payload, timeout=timeout)

    if not isinstance(data, dict):
        return "Không nhận được phản hồi hợp lệ từ ChatGPT."

    if "error" in data:
        msg = data.get("error", {}).get("message") or str(data.get("error"))
        return f"Lỗi khi gọi ChatGPT: {msg}"

    try:
        choices = data.get("choices") or []
        if not choices:
            return "ChatGPT không có phản hồi."
        content = choices[0]["message"]["content"].strip()
        return content or ""
    except Exception:
        return "Không phân tích được phản hồi từ ChatGPT."


# Minimal feature glue so the module can be routed like others
keywords = ["chatgpt", "hoi chatgpt", "hỏi chatgpt", "gpt"]
patterns = ["hỏi chatgpt", "hoi chatgpt", "chatgpt oi", "chatgpt ơi"]


def main(command: Optional[str] = None) -> str:
    """Entry point for manual ChatGPT queries.

    Examples:
    - "hỏi chatgpt Java và Python khác gì?"
    - "chatgpt ơi, viết đoạn mã Python in hello"
    """
    text = (command or "").strip()
    if not is_configured():
        return (
            "Chưa cấu hình ChatGPT. Đặt biến môi trường OPENAI_API_KEY, "
            "(tuỳ chọn) OPENAI_MODEL=gpt-4o-mini để bật."
        )

    # Strip leading trigger phrases to keep prompt clean
    lowered = text.lower()
    for trig in ["hỏi chatgpt", "hoi chatgpt", "chatgpt ơi", "chatgpt oi"]:
        if lowered.startswith(trig):
            text = text[len(trig):].strip(" :，,:-\t")
            break

    if not text:
        return "Bạn muốn hỏi ChatGPT điều gì?"

    return ask_chatgpt(text)
