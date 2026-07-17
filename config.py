"""Environment-based configuration with secure MQTT defaults."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re

from dotenv import load_dotenv


GATEWAY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LOCAL_BROKERS = {"localhost", "127.0.0.1", "::1"}


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True, slots=True)
class Settings:
    mqtt_enabled: bool
    mqtt_broker: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_username: str | None
    mqtt_password: str | None
    mqtt_tls: bool
    mqtt_ca_cert: str | None
    mqtt_client_cert: str | None
    mqtt_client_key: str | None
    mqtt_allow_insecure_remote: bool
    mqtt_client_id: str | None
    gateway_id: str
    gateway_ip: str | None
    gateway_publish_interval: int
    gateway_stale_seconds: int
    max_gateways: int
    http_host: str
    http_port: int
    http_hsts: bool
    http_trusted_hosts: list[str] | None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        broker = os.getenv("MQTT_BROKER", "localhost").strip()
        if not broker or any(character in broker for character in "/# +"):
            raise ValueError("MQTT_BROKER must be a hostname or IP address")

        tls = _bool("MQTT_TLS", broker.lower() not in LOCAL_BROKERS)
        port = _int(
            "MQTT_PORT",
            8883 if tls else 1883,
            minimum=1,
            maximum=65535,
        )
        topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "lora/gateways").strip(" /")
        if not topic_prefix or "+" in topic_prefix or "#" in topic_prefix:
            raise ValueError("MQTT_TOPIC_PREFIX cannot be empty or contain wildcards")

        username = _optional("MQTT_USERNAME")
        password = _optional("MQTT_PASSWORD")
        if bool(username) != bool(password):
            raise ValueError("MQTT_USERNAME and MQTT_PASSWORD must be set together")

        client_cert = _optional("MQTT_CLIENT_CERT")
        client_key = _optional("MQTT_CLIENT_KEY")
        if bool(client_cert) != bool(client_key):
            raise ValueError("MQTT_CLIENT_CERT and MQTT_CLIENT_KEY must be set together")
        if (client_cert or _optional("MQTT_CA_CERT")) and not tls:
            raise ValueError("MQTT_TLS must be enabled when MQTT certificates are configured")

        allow_insecure = _bool("MQTT_ALLOW_INSECURE_REMOTE", False)
        if not tls and broker.lower() not in LOCAL_BROKERS and not allow_insecure:
            raise ValueError(
                "Plaintext MQTT to a remote broker is blocked. Enable MQTT_TLS or "
                "explicitly set MQTT_ALLOW_INSECURE_REMOTE=true for an isolated test network."
            )
        if broker.lower() not in LOCAL_BROKERS and not (username or client_cert):
            raise ValueError(
                "Remote MQTT requires authentication. Configure MQTT_USERNAME and "
                "MQTT_PASSWORD or a client certificate and key."
            )

        gateway_id = os.getenv("GATEWAY_ID", "lora-gateway-01").strip()
        if not GATEWAY_ID_PATTERN.fullmatch(gateway_id):
            raise ValueError(
                "GATEWAY_ID must be 1-64 letters, numbers, dots, underscores, or hyphens"
            )

        trusted_hosts_raw = _optional("HTTP_TRUSTED_HOSTS")
        trusted_hosts = (
            [host.strip() for host in trusted_hosts_raw.split(",") if host.strip()]
            if trusted_hosts_raw
            else None
        )

        return cls(
            mqtt_enabled=_bool("MQTT_ENABLED", False),
            mqtt_broker=broker,
            mqtt_port=port,
            mqtt_topic_prefix=topic_prefix,
            mqtt_username=username,
            mqtt_password=password,
            mqtt_tls=tls,
            mqtt_ca_cert=_optional("MQTT_CA_CERT"),
            mqtt_client_cert=client_cert,
            mqtt_client_key=client_key,
            mqtt_allow_insecure_remote=allow_insecure,
            mqtt_client_id=_optional("MQTT_CLIENT_ID"),
            gateway_id=gateway_id,
            gateway_ip=_optional("GATEWAY_IP"),
            gateway_publish_interval=_int(
                "GATEWAY_PUBLISH_INTERVAL", 60, minimum=5, maximum=86400
            ),
            gateway_stale_seconds=_int(
                "GATEWAY_STALE_SECONDS", 180, minimum=10, maximum=604800
            ),
            max_gateways=_int("MAX_GATEWAYS", 100, minimum=1, maximum=10000),
            http_host=os.getenv("HTTP_HOST", "127.0.0.1").strip(),
            http_port=_int("HTTP_PORT", 5000, minimum=1, maximum=65535),
            http_hsts=_bool("HTTP_HSTS", False),
            http_trusted_hosts=trusted_hosts or ["localhost", "127.0.0.1", "[::1]"],
        )
