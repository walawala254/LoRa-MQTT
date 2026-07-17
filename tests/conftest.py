from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from config import Settings
from telemetry import GatewayTelemetry


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name in (
        "MQTT_ENABLED",
        "MQTT_BROKER",
        "MQTT_PORT",
        "MQTT_TOPIC_PREFIX",
        "MQTT_USERNAME",
        "MQTT_PASSWORD",
        "MQTT_TLS",
        "MQTT_CA_CERT",
        "MQTT_CLIENT_CERT",
        "MQTT_CLIENT_KEY",
        "MQTT_ALLOW_INSECURE_REMOTE",
        "MQTT_CLIENT_ID",
        "GATEWAY_ID",
        "GATEWAY_IP",
        "GATEWAY_PUBLISH_INTERVAL",
        "GATEWAY_STALE_SECONDS",
        "MAX_GATEWAYS",
        "HTTP_HOST",
        "HTTP_PORT",
        "HTTP_HSTS",
        "HTTP_TRUSTED_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)
    return replace(Settings.from_env(), mqtt_enabled=False)


@pytest.fixture
def online_telemetry() -> GatewayTelemetry:
    return GatewayTelemetry(
        gateway_id="gateway-01",
        ip="192.168.1.42",
        reported_status="online",
        reported_at=datetime.now(UTC),
    )
