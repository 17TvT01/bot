import os
import json
from typing import Optional, List


DEFAULT_PROVIDER_KEY = "DEFAULT_PROVIDER"  # values: "chatgpt" | "gemini"


def _config_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(root, "assistant_config.json")


def _load_config() -> dict:
    try:
        p = _config_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_config(cfg: dict) -> None:
    try:
        p = _config_path()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_default_provider() -> Optional[str]:
    val = _load_config().get(DEFAULT_PROVIDER_KEY)
    if isinstance(val, str) and val.lower() in ("chatgpt", "gemini"):
        return val.lower()
    return None


def set_default_provider(provider: Optional[str]) -> None:
    cfg = _load_config()
    if provider is None:
        cfg.pop(DEFAULT_PROVIDER_KEY, None)
    else:
        pv = str(provider).lower().strip()
        if pv not in ("chatgpt", "gemini"):
            return
        cfg[DEFAULT_PROVIDER_KEY] = pv
    _save_config(cfg)


def list_configured_providers() -> List[str]:
    out: List[str] = []
    try:
        from features.chatgpt_bridge import is_configured as cg_conf  # type: ignore
        if cg_conf():
            out.append("chatgpt")
    except Exception:
        pass
    try:
        from features.gemini_bridge import is_configured as gm_conf  # type: ignore
        if gm_conf():
            out.append("gemini")
    except Exception:
        pass
    return out

