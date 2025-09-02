import json
import time
import re
from typing import Dict, Any, Optional, Tuple

# Optional requests import (real API if available)
try:
    import requests  # type: ignore
except Exception:
    requests = None

# In-memory cache: {normalized_city: (timestamp, data)}
_weather_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 10 * 60  # 10 minutes

# Minimal city -> (lat, lon) mapping for VN majors
_CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "hanoi": (21.0278, 105.8342),
    "ha noi": (21.0278, 105.8342),
    "ho chi minh": (10.8231, 106.6297),
    "tp ho chi minh": (10.8231, 106.6297),
    "hcm": (10.8231, 106.6297),
    "saigon": (10.7769, 106.7009),
    "da nang": (16.0544, 108.2022),
    "hue": (16.4637, 107.5909),
    "nha trang": (12.2388, 109.1967),
    "can tho": (10.0452, 105.7469),
    "hai phong": (20.8449, 106.6881),
    "vung tau": (10.4114, 107.1362),
}

_WEATHER_CODE_MAP_VI = {
    0: "Trời quang", 1: "Ít mây", 2: "Có mây", 3: "Nhiều mây",
    45: "Sương mù", 48: "Sương mù đóng băng",
    51: "Mưa phùn nhẹ", 53: "Mưa phùn vừa", 55: "Mưa phùn dày",
    61: "Mưa nhẹ", 63: "Mưa vừa", 65: "Mưa to",
    66: "Mưa đóng băng nhẹ", 67: "Mưa đóng băng to",
    71: "Tuyết nhẹ", 73: "Tuyết vừa", 75: "Tuyết to",
    80: "Mưa rào nhẹ", 81: "Mưa rào vừa", 82: "Mưa rào to",
    95: "Dông", 96: "Dông có mưa đá nhẹ", 97: "Dông có mưa đá",
}

def _normalize_city(text: Optional[str]) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _from_cache(city_norm: str) -> Optional[Dict[str, Any]]:
    entry = _weather_cache.get(city_norm)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts <= _CACHE_TTL_SECONDS:
        return data
    _weather_cache.pop(city_norm, None)
    return None

def _put_cache(city_norm: str, data: Dict[str, Any]) -> None:
    _weather_cache[city_norm] = (time.time(), data)

def _fmt_output(city_display: str, temp_c: float, humidity: Optional[float], code: Optional[int]) -> str:
    lines = [f"Thời tiết tại {city_display}:"]
    lines.append(f"• Nhiệt độ: {round(temp_c, 1)}°C")
    if humidity is not None:
        lines.append(f"• Độ ẩm: {int(round(humidity))}%")
    if code is not None:
        lines.append(f"• Tình trạng: {_WEATHER_CODE_MAP_VI.get(int(code), 'Không rõ')}")
    return "\n".join(lines)

def _simulated(city: str) -> str:
    samples = {
        "hanoi": {"temp": 28.0, "humidity": 75, "code": 2},
        "ho chi minh": {"temp": 32.0, "humidity": 80, "code": 1},
        "da nang": {"temp": 30.0, "humidity": 85, "code": 80},
    }
    key = _normalize_city(city)
    data = samples.get(key, {"temp": 27.0, "humidity": 70, "code": 2})
    return _fmt_output(city or "(không rõ)", data["temp"], data["humidity"], data["code"])

def _query_open_meteo(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    if not requests:
        return None
    try:
        # Modern endpoint with current fields
        url = (
            "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code&timezone=auto"
        ).format(lat=lat, lon=lon)
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            j = r.json()
            cur = j.get("current") or {}
            if cur:
                return {
                    "temp": float(cur.get("temperature_2m")),
                    "humidity": float(cur.get("relative_humidity_2m")) if cur.get("relative_humidity_2m") is not None else None,
                    "code": int(cur.get("weather_code")) if cur.get("weather_code") is not None else None,
                }
        # Legacy fallback (older Open‑Meteo)
        url2 = (
            "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current_weather=true&timezone=auto"
        ).format(lat=lat, lon=lon)
        r2 = requests.get(url2, timeout=5)
        if r2.status_code == 200:
            j2 = r2.json()
            cw = j2.get("current_weather") or {}
            if cw:
                return {
                    "temp": float(cw.get("temperature")),
                    "humidity": None,
                    "code": int(cw.get("weathercode")) if cw.get("weathercode") is not None else None,
                }
    except Exception:
        return None
    return None

def get_weather(city_name: str = None) -> str:
    """Get current weather (Open‑Meteo if available) with caching and fallback."""
    city = city_name or "Hanoi"
    city_norm = _normalize_city(city)

    cached = _from_cache(city_norm)
    if cached:
        return _fmt_output(city.title(), cached.get("temp", 0.0), cached.get("humidity"), cached.get("code"))

    coords = _CITY_COORDS.get(city_norm)
    if coords and requests:
        data = _query_open_meteo(coords[0], coords[1])
        if data:
            _put_cache(city_norm, data)
            return _fmt_output(city.title(), data.get("temp", 0.0), data.get("humidity"), data.get("code"))

    return _simulated(city)

def weather(command: str = None) -> str:
    """Parse command to extract city name and return weather info."""
    city_name = None
    if command:
        tokens = command.lower().split()
        city_keywords = ["o", "tại", "tai", "thanh pho", "tp", "in", "ở"]
        for kw in city_keywords:
            if kw in tokens:
                idx = tokens.index(kw)
                city_name = " ".join(tokens[idx + 1:])
                break
        if not city_name:
            weather_words = ["thoi tiet", "weather", "nhiet do", "do am", "du bao"]
            city_tokens = [t for t in tokens if t not in weather_words]
            if city_tokens:
                city_name = " ".join(city_tokens)

    return get_weather(city_name)

# Keywords and patterns for feature detection
keywords = ["thời tiết", "weather", "nhiệt độ", "độ ẩm", "dự báo", "thoi tiet", "nhiet do", "do am"]
patterns = [
    "thời tiết ở",
    "thời tiết tại",
    "nhiệt độ ở",
    "weather in",
    "dự báo thời tiết",
]

def get_weather_powershell(city_name: str) -> str:
    """Kept for compatibility: delegates to main get_weather with fallback."""
    return get_weather(city_name)

