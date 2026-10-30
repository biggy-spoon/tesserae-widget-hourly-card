"""weather_hourly_card smoke: renders at every supported size and the fetch
shapes Open-Meteo's answer into the card's fields."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

_FAKE_PAYLOAD = json.dumps(
    {
        "current": {
            "time": "2026-06-01T09:30",
            "temperature_2m": 14.2,
            "apparent_temperature": 12.8,
            "weather_code": 3,
            "is_day": 1,
        },
        "hourly": {
            "time": [f"2026-06-{day:02d}T{h:02d}:00" for day in (1, 2) for h in range(24)],
            "temperature_2m": [10 + h % 12 for _ in (1, 2) for h in range(24)],
            "weather_code": [3] * 48,
            "is_day": [1 if 6 <= h < 18 else 0 for _ in (1, 2) for h in range(24)],
            "precipitation_probability": [30] * 48,
        },
        "daily": {"temperature_2m_max": [19.0, 20.0], "temperature_2m_min": [8.0, 9.0]},
    }
).encode()


class _FakeResp:
    def read(self) -> bytes:
        return _FAKE_PAYLOAD

    def __enter__(self):
        return self

    def __exit__(self, *a) -> bool:
        return False


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_weather_hourly_card_renders(client: FlaskClient, size: str) -> None:
    opts = '{"location":{"name":"Springfield","latitude":40.0,"longitude":-89.0},"label":"Springfield","units":"metric"}'
    with patch("urllib.request.urlopen", return_value=_FakeResp()):
        resp = client.get(f"/_test/render?plugin=weather_hourly_card&size={size}&opts={opts}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'data-plugin="weather_hourly_card"' in body
    assert "Springfield" in body
    # Feels-like, chance of rain and the as-of time are all threaded through.
    assert "12.8" in body
    assert '"precip": 30' in body or '"precip":30' in body
    assert '"asof_hour": 9' in body or '"asof_hour":9' in body
    # The window starts at the current hour (09:00), not midnight.
    assert '"hour": 9' in body or '"hour":9' in body


def test_clock_option_and_translation_keys(client: FlaskClient) -> None:
    opts = (
        '{"location":{"name":"Springfield","latitude":40.0,"longitude":-89.0},'
        '"label":"Springfield","units":"metric","time_format":"24h"}'
    )
    with patch("urllib.request.urlopen", return_value=_FakeResp()):
        resp = client.get(f"/_test/render?plugin=weather_hourly_card&size=lg&opts={opts}")
    body = resp.get_data(as_text=True)
    assert '"time_format": "24h"' in body or '"time_format":"24h"' in body
    # The condition travels as a strings key (3 = overcast) plus English text.
    assert '"cond_key": "cond_cloudy"' in body or '"cond_key":"cond_cloudy"' in body


def test_manifest_declares_network_and_clock() -> None:
    manifest = json.loads((Path(__file__).parent.parent / "plugin.json").read_text())
    assert manifest["requires"] == ["network:api.open-meteo.com"]
    clock = next(o for o in manifest["cell_options"] if o["name"] == "time_format")
    assert {c["value"] for c in clock["choices"]} == {"12h", "24h"}
    strings = json.loads((Path(__file__).parent.parent / "strings" / "en.json").read_text())
    for key in ("title", "feels", "as_of", "high", "low", "am", "pm", "pick_location", "cond_cloudy"):
        assert key in strings


def test_no_location_is_an_empty_state(client: FlaskClient) -> None:
    resp = client.get("/_test/render?plugin=weather_hourly_card&size=md&opts={}")
    assert resp.status_code == 200
    assert "Pick a location" in resp.get_data(as_text=True)
