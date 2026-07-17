"""Validation and in-memory state for gateway telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import ipaddress
import json
import threading
from typing import Any

from config import GATEWAY_ID_PATTERN


MAX_PAYLOAD_BYTES = 4096
ALLOWED_FIELDS = {"schema_version", "gateway_id", "ip", "status", "timestamp"}


class TelemetryError(ValueError):
    """Raised when untrusted MQTT telemetry is malformed."""


@dataclass(frozen=True, slots=True)
class GatewayTelemetry:
    gateway_id: str
    ip: str | None
    reported_status: str
    reported_at: datetime


@dataclass(frozen=True, slots=True)
class GatewayRecord:
    telemetry: GatewayTelemetry
    received_at: datetime


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise TelemetryError("payload contains duplicate fields")
        document[key] = value
    return document


def parse_telemetry(payload: bytes, topic_gateway_id: str) -> GatewayTelemetry:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise TelemetryError("payload exceeds 4096 bytes")
    try:
        document = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TelemetryError("payload must be valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise TelemetryError("payload must be a JSON object")
    if set(document) - ALLOWED_FIELDS:
        raise TelemetryError("payload contains unsupported fields")
    if document.get("schema_version") != 1:
        raise TelemetryError("unsupported schema_version")

    gateway_id = document.get("gateway_id")
    if not isinstance(gateway_id, str) or not GATEWAY_ID_PATTERN.fullmatch(gateway_id):
        raise TelemetryError("invalid gateway_id")
    if gateway_id != topic_gateway_id:
        raise TelemetryError("topic and payload gateway IDs do not match")

    status = document.get("status")
    if status not in {"online", "offline"}:
        raise TelemetryError("status must be online or offline")

    raw_ip = document.get("ip")
    ip: str | None
    if status == "online":
        if not isinstance(raw_ip, str):
            raise TelemetryError("online telemetry requires an IP address")
        try:
            ip = str(ipaddress.ip_address(raw_ip))
        except ValueError as exc:
            raise TelemetryError("invalid IP address") from exc
    elif raw_ip is None:
        ip = None
    else:
        try:
            ip = str(ipaddress.ip_address(raw_ip))
        except (TypeError, ValueError) as exc:
            raise TelemetryError("invalid IP address") from exc

    raw_timestamp = document.get("timestamp")
    if not isinstance(raw_timestamp, str) or len(raw_timestamp) > 40:
        raise TelemetryError("timestamp must be an ISO-8601 string")
    try:
        reported_at = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryError("invalid timestamp") from exc
    if reported_at.tzinfo is None:
        raise TelemetryError("timestamp must include a timezone")
    reported_at = reported_at.astimezone(UTC)
    if reported_at > datetime.now(UTC) + timedelta(minutes=5):
        raise TelemetryError("timestamp is too far in the future")

    return GatewayTelemetry(gateway_id, ip, status, reported_at)


class GatewayStore:
    def __init__(self, *, stale_after_seconds: int, max_gateways: int = 100) -> None:
        self._stale_after_seconds = stale_after_seconds
        self._max_gateways = max_gateways
        self._records: dict[str, GatewayRecord] = {}
        self._lock = threading.RLock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def update(self, telemetry: GatewayTelemetry) -> bool:
        with self._lock:
            current = self._records.get(telemetry.gateway_id)
            if current and telemetry.reported_at < current.telemetry.reported_at:
                return False
            if current is None and len(self._records) >= self._max_gateways:
                return False
            self._records[telemetry.gateway_id] = GatewayRecord(
                telemetry=telemetry,
                received_at=datetime.now(UTC),
            )
            return True

    def snapshot(self, gateway_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._records.get(gateway_id)
        return self._serialize(record) if record else None

    def snapshots(self) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
        return sorted(
            (self._serialize(record) for record in records),
            key=lambda item: item["gateway_id"],
        )

    def _serialize(self, record: GatewayRecord) -> dict[str, Any]:
        now = datetime.now(UTC)
        age_seconds = max(0, int((now - record.telemetry.reported_at).total_seconds()))
        if record.telemetry.reported_status == "offline":
            status = "offline"
        elif age_seconds > self._stale_after_seconds:
            status = "stale"
        else:
            status = "online"
        return {
            "gateway_id": record.telemetry.gateway_id,
            "ip": record.telemetry.ip,
            "status": status,
            "reported_status": record.telemetry.reported_status,
            "last_seen": _isoformat(record.telemetry.reported_at),
            "received_at": _isoformat(record.received_at),
            "age_seconds": age_seconds,
        }


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
