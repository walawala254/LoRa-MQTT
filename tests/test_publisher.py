from __future__ import annotations

from dataclasses import replace
import json

from config import Settings
from mqtt_client import make_payload


def test_online_payload_has_only_the_documented_fields(settings: Settings) -> None:
    configured = replace(settings, gateway_ip="10.10.0.8")

    payload = json.loads(make_payload(configured, "online"))

    assert payload["schema_version"] == 1
    assert payload["gateway_id"] == "lora-gateway-01"
    assert payload["ip"] == "10.10.0.8"
    assert payload["status"] == "online"
    assert set(payload) == {"schema_version", "gateway_id", "ip", "status", "timestamp"}
