from __future__ import annotations

import pytest

from config import Settings


def test_remote_plaintext_mqtt_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setenv("MQTT_BROKER", "broker.example.net")
    monkeypatch.setenv("MQTT_TLS", "false")

    with pytest.raises(ValueError, match="Plaintext MQTT"):
        Settings.from_env()


def test_remote_mqtt_defaults_to_tls(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setenv("MQTT_BROKER", "broker.example.net")
    monkeypatch.setenv("MQTT_USERNAME", "monitor")
    monkeypatch.setenv("MQTT_PASSWORD", "test-only-password")

    configured = Settings.from_env()

    assert configured.mqtt_tls is True
    assert configured.mqtt_port == 8883


def test_remote_anonymous_mqtt_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setenv("MQTT_BROKER", "broker.example.net")

    with pytest.raises(ValueError, match="requires authentication"):
        Settings.from_env()


def test_credentials_must_be_a_pair(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setenv("MQTT_USERNAME", "monitor")

    with pytest.raises(ValueError, match="must be set together"):
        Settings.from_env()


def test_gateway_id_cannot_inject_a_topic(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setenv("GATEWAY_ID", "gateway/+/status")

    with pytest.raises(ValueError, match="GATEWAY_ID"):
        Settings.from_env()
