import os
import json
import threading
from typing import Optional, Dict, Any, List, Tuple


_tts_engine = None
_tts_lock = threading.RLock()


def _config_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(root, "assistant_config.json")


def _load_config() -> Dict[str, Any]:
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


def _save_config(cfg: Dict[str, Any]) -> None:
    try:
        p = _config_path()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_tts_enabled() -> bool:
    return bool(_load_config().get("VOICE_TTS_ENABLED", False))


def get_tts_rate() -> int:
    try:
        return int(_load_config().get("VOICE_RATE", 170))
    except Exception:
        return 170


def get_tts_volume() -> float:
    try:
        v = float(_load_config().get("VOICE_VOLUME", 1.0))
        return max(0.0, min(1.0, v))
    except Exception:
        return 1.0


def get_tts_voice_id() -> Optional[str]:
    v = _load_config().get("VOICE_VOICE_ID")
    return str(v) if v else None


def list_voices() -> List[Tuple[str, str]]:
    try:
        import pyttsx3  # type: ignore
        eng = pyttsx3.init()
        arr = []
        for v in eng.getProperty("voices"):
            try:
                arr.append((v.id, getattr(v, "name", v.id)))
            except Exception:
                pass
        return arr
    except Exception:
        return []


def _ensure_engine(rate: Optional[int] = None, volume: Optional[float] = None, voice_id: Optional[str] = None):
    global _tts_engine
    with _tts_lock:
        try:
            import pyttsx3  # type: ignore
        except Exception:
            return None
        if _tts_engine is None:
            try:
                _tts_engine = pyttsx3.init()
            except Exception:
                return None
        # Apply properties
        try:
            r = int(rate if rate is not None else get_tts_rate())
            _tts_engine.setProperty("rate", r)
        except Exception:
            pass
        try:
            v = float(volume if volume is not None else get_tts_volume())
            _tts_engine.setProperty("volume", max(0.0, min(1.0, v)))
        except Exception:
            pass
        vid = voice_id if voice_id is not None else get_tts_voice_id()
        if vid:
            try:
                _tts_engine.setProperty("voice", vid)
            except Exception:
                pass
        return _tts_engine


def speak_text(text: str, *, rate: Optional[int] = None, volume: Optional[float] = None, voice_id: Optional[str] = None) -> bool:
    eng = _ensure_engine(rate=rate, volume=volume, voice_id=voice_id)
    if eng is None:
        return False
    try:
        with _tts_lock:
            eng.stop()
            eng.say(text)
            eng.runAndWait()
        return True
    except Exception:
        return False


def set_voice_config(*, enabled: Optional[bool] = None, rate: Optional[int] = None, volume: Optional[float] = None, voice_id: Optional[str] = None) -> None:
    cfg = _load_config()
    if enabled is not None:
        cfg["VOICE_TTS_ENABLED"] = bool(enabled)
    if rate is not None:
        try:
            cfg["VOICE_RATE"] = int(rate)
        except Exception:
            pass
    if volume is not None:
        try:
            cfg["VOICE_VOLUME"] = float(volume)
        except Exception:
            pass
    if voice_id is not None:
        cfg["VOICE_VOICE_ID"] = str(voice_id)
    _save_config(cfg)
    # Apply immediately
    _ensure_engine(rate=cfg.get("VOICE_RATE"), volume=cfg.get("VOICE_VOLUME"), voice_id=cfg.get("VOICE_VOICE_ID"))


def transcribe_once(timeout: float = 5.0, phrase_time_limit: float = 10.0, language: str = "vi-VN") -> Optional[str]:
    try:
        import speech_recognition as sr  # type: ignore
    except Exception:
        return None
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        # Try Google first
        try:
            return r.recognize_google(audio, language=language)
        except Exception:
            pass
        # Fallback to Sphinx (if installed)
        try:
            return r.recognize_sphinx(audio, language=language)
        except Exception:
            return None
    except Exception:
        return None

