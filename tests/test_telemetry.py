from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json

import pytest

from telemetry import GatewayStore, GatewayTelemetry, TelemetryError, parse_telemetry


def payload(**overrides: object) -> bytes:
    document = {
        "schema_version": 1,
        "gateway_id": "gateway-01",
        "ip": "192.168.1.42",
        "status": "online",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    document.update(overrides)
    return json.dumps(document).encode()


def test_valid_telemetry_is_normalized() -> None:
    telemetry = parse_telemetry(payload(ip="2001:0db8::1"), "gateway-01")

    assert telemetry.gateway_id == "gateway-01"
    assert telemetry.ip == "2001:db8::1"


@pytest.mark.parametrize(
    ("body", "topic_id"),
    [
        (payload(gateway_id="someone-else"), "gateway-01"),
        (payload(ip="not-an-ip"), "gateway-01"),
        (payload(status="compromised"), "gateway-01"),
        (payload(extra="unexpected"), "gateway-01"),
        (b"not-json", "gateway-01"),
    ],
)
def test_untrusted_payloads_are_rejected(body: bytes, topic_id: str) -> None:
    with pytest.raises(TelemetryError):
        parse_telemetry(body, topic_id)


def test_stale_gateway_is_reported_as_stale() -> None:
    store = GatewayStore(stale_after_seconds=60)
    store.update(
        GatewayTelemetry(
            gateway_id="gateway-01",
            ip="192.168.1.42",
            reported_status="online",
            reported_at=datetime.now(UTC) - timedelta(minutes=2),
        )
    )

    assert store.snapshot("gateway-01")["status"] == "stale"


def test_older_replayed_status_does_not_replace_current_status() -> None:
    store = GatewayStore(stale_after_seconds=60)
    now = datetime.now(UTC)
    current = GatewayTelemetry("gateway-01", "192.168.1.42", "online", now)
    replay = GatewayTelemetry(
        "gateway-01", "192.168.1.99", "offline", now - timedelta(minutes=1)
    )

    store.update(current)
    store.update(replay)

    assert store.snapshot("gateway-01")["ip"] == "192.168.1.42"
    assert store.snapshot("gateway-01")["reported_status"] == "online"


def test_duplicate_json_fields_are_rejected() -> None:
    body = (
        b'{"schema_version":1,"gateway_id":"gateway-01","gateway_id":"gateway-02",'
        b'"ip":"192.168.1.42","status":"online","timestamp":"2026-01-01T00:00:00Z"}'
    )

    with pytest.raises(TelemetryError, match="duplicate"):
        parse_telemetry(body, "gateway-01")


def test_gateway_store_capacity_is_bounded() -> None:
    store = GatewayStore(stale_after_seconds=60, max_gateways=1)
    now = datetime.now(UTC)

    assert store.update(GatewayTelemetry("gateway-01", "10.0.0.1", "online", now))
    assert not store.update(GatewayTelemetry("gateway-02", "10.0.0.2", "online", now))
    assert store.count == 1
