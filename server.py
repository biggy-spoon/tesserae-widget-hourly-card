"""Today's hourly forecast card: current temp + feels-like, chance of rain,
today's hi/lo, next N hours.

One Open-Meteo call (current + daily hi/lo + hourly), cached for 10 minutes
per (lat, lon, units, hours). All times are the location's own local time
(``timezone=auto``), so the "as of" stamp and the hour labels are correct
no matter what zone the server container runs in.
"""

from __future__ import annotations

import contextlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.plugin_http import fetch_json

CACHE_TTL_S = 600
HTTP_TIMEOUT_S = 5
USER_AGENT = "tesserae/0.1 (+weather_hourly_card)"
ALLOWED_HOURS = (4, 5, 6, 8)

# WMO code -> (day icon, night icon, description)
_WMO: dict[int, tuple[str, str, str]] = {
    0: ("sun", "moon", "Clear"),
    1: ("sun", "moon", "Mostly clear"),
    2: ("partly", "partly-night", "Partly cloudy"),
    3: ("cloud", "cloud", "Cloudy"),
    45: ("fog", "fog", "Fog"),
    48: ("fog", "fog", "Fog"),
    51: ("drizzle", "drizzle", "Drizzle"),
    53: ("drizzle", "drizzle", "Drizzle"),
    55: ("drizzle", "drizzle", "Drizzle"),
    56: ("drizzle", "drizzle", "Freezing drizzle"),
    57: ("drizzle", "drizzle", "Freezing drizzle"),
    61: ("rain", "rain", "Rain"),
    63: ("rain", "rain", "Rain"),
    65: ("rain-heavy", "rain-heavy", "Heavy rain"),
    66: ("rain", "rain", "Freezing rain"),
    67: ("rain-heavy", "rain-heavy", "Freezing rain"),
    71: ("snow", "snow", "Snow"),
    73: ("snow", "snow", "Snow"),
    75: ("snow", "snow", "Heavy snow"),
    77: ("snow", "snow", "Snow grains"),
    80: ("showers", "showers", "Showers"),
    81: ("showers", "showers", "Showers"),
    82: ("rain-heavy", "rain-heavy", "Heavy showers"),
    85: ("snow", "snow", "Snow showers"),
    86: ("snow", "snow", "Snow showers"),
    95: ("storm", "storm", "Thunderstorm"),
    96: ("storm", "storm", "Thunderstorm"),
    99: ("storm", "storm", "Thunderstorm"),
}


def _info(code: Any, is_day: bool) -> tuple[str, str]:
    try:
        entry = _WMO.get(int(code))
    except (TypeError, ValueError):
        entry = None
    if entry is None:
        return "cloud", ""
    return (entry[0] if is_day else entry[1]), entry[2]


def _cached(path: Path) -> dict[str, Any] | None:
    if not path.exists() or time.time() - path.stat().st_mtime >= CACHE_TTL_S:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _parse(iso: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(iso))
    except (ValueError, TypeError):
        return None


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, int | float) else None


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings
    label = options.get("label", "")
    lat_raw, lon_raw = options.get("latitude"), options.get("longitude")
    if lat_raw in (None, "") or lon_raw in (None, ""):
        return {"error": "Pick a location in the cell editor.", "label": label}
    try:
        lat, lon = float(lat_raw), float(lon_raw)
    except (TypeError, ValueError):
        return {"error": "Location has invalid coordinates.", "label": label}
    units = "metric" if str(options.get("units", "imperial")) == "metric" else "imperial"
    try:
        hours = int(options.get("hours", 6))
    except (TypeError, ValueError):
        hours = 6
    if hours not in ALLOWED_HOURS:
        hours = 6

    data_dir = Path(ctx["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = data_dir / f"card_{lat:.3f}_{lon:.3f}_{units}_{hours}.json"
    cached = _cached(cache_path)
    if cached is not None:
        cached["label"] = label
        return cached

    temp_unit = "fahrenheit" if units == "imperial" else "celsius"
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,weather_code,is_day"
        "&hourly=temperature_2m,weather_code,is_day,precipitation_probability"
        "&daily=temperature_2m_max,temperature_2m_min"
        f"&temperature_unit={temp_unit}"
        "&forecast_days=2&timezone=auto"
    )
    try:
        payload = fetch_json(
            url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_S, retries=0
        )
    except Exception as err:
        return {"error": f"{type(err).__name__}: {err}"}

    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}
    now_dt = _parse(current.get("time"))
    now_hour = now_dt.replace(minute=0, second=0, microsecond=0) if now_dt else None

    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []
    days = hourly.get("is_day") or []
    rain = hourly.get("precipitation_probability") or []
    start = 0
    if now_hour is not None:
        for i, iso in enumerate(times):
            t = _parse(iso)
            if t is not None and t >= now_hour:
                start = i
                break

    slots: list[dict[str, Any]] = []
    for i in range(start, min(len(times), start + hours)):
        t = _parse(times[i])
        temp = _num(temps[i]) if i < len(temps) else None
        if t is None or temp is None:
            continue
        is_day = bool(days[i]) if i < len(days) else 6 <= t.hour < 18
        icon, _ = _info(codes[i] if i < len(codes) else None, is_day)
        slots.append({"hour": t.hour, "temp": temp, "icon": icon})

    # Chance of precipitation for the current hour (Open-Meteo has no
    # probability in ``current``, so read it off the hourly slot).
    precip = _num(rain[start]) if start < len(rain) else None
    cur_icon, cond = _info(current.get("weather_code"), bool(current.get("is_day", 1)))
    his = daily.get("temperature_2m_max") or []
    los = daily.get("temperature_2m_min") or []
    result = {
        "label": label,
        "units": units,
        "now": _num(current.get("temperature_2m")),
        "feels": _num(current.get("apparent_temperature")),
        "precip": round(precip) if precip is not None else None,
        "icon": cur_icon,
        "cond": cond,
        "hi": _num(his[0]) if his else None,
        "lo": _num(los[0]) if los else None,
        "asof_hour": now_dt.hour if now_dt else None,
        "asof_minute": now_dt.minute if now_dt else None,
        "slots": slots,
    }
    with contextlib.suppress(OSError):
        cache_path.write_text(json.dumps(result), encoding="utf-8")
    return result
