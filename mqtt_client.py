"""Gateway-side MQTT publisher.

Run this process on the Raspberry Pi or other LoRa gateway host.
"""

from __future__ import annotations

from datetime import UTC, datetime
import ipaddress
import json
import logging
import signal
import socket
import threading
import time

import paho.mqtt.client as mqtt

from config import Settings
from mqtt_service import configure_client


LOGGER = logging.getLogger(__name__)


def discover_ip(settings: Settings) -> str:
    if settings.gateway_ip:
        return str(ipaddress.ip_address(settings.gateway_ip))

    addresses: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect((settings.mqtt_broker, settings.mqtt_port))
            addresses.append(connection.getsockname()[0])
    except OSError:
        pass

    try:
        for result in socket.getaddrinfo(socket.gethostname(), None):
            addresses.append(result[4][0])
    except OSError:
        pass

    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if not parsed.is_loopback and not parsed.is_link_local:
            return str(parsed)

    if addresses:
        return str(ipaddress.ip_address(addresses[0]))
    raise RuntimeError("Unable to determine the gateway IP; set GATEWAY_IP explicitly")


def make_payload(settings: Settings, status: str) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "gateway_id": settings.gateway_id,
            "ip": discover_ip(settings) if status == "online" else None,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


class GatewayPublisher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connected = threading.Event()
        self._stop = threading.Event()
        self._topic = f"{settings.mqtt_topic_prefix}/{settings.gateway_id}/status"
        client_id = settings.mqtt_client_id or f"gateway-{settings.gateway_id}"
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        configure_client(self._client, settings)
        self._client.will_set(
            self._topic,
            payload=make_payload(settings, "offline"),
            qos=1,
            retain=True,
        )
        self._client.on_connect = self._on_connect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.on_disconnect = self._on_disconnect

    def run(self) -> None:
        self._client.connect_async(
            self._settings.mqtt_broker,
            self._settings.mqtt_port,
            keepalive=60,
        )
        self._client.loop_start()
        LOGGER.info("Gateway publisher started as %s", self._settings.gateway_id)
        next_publish = 0.0
        try:
            while not self._stop.wait(1):
                if self._connected.is_set() and time.monotonic() >= next_publish:
                    self.publish("online")
                    next_publish = time.monotonic() + self._settings.gateway_publish_interval
        finally:
            if self._connected.is_set():
                info = self.publish("offline")
                info.wait_for_publish(timeout=3)
            self._client.disconnect()
            self._client.loop_stop()

    def stop(self, *_args: object) -> None:
        self._stop.set()

    def publish(self, status: str) -> mqtt.MQTTMessageInfo:
        info = self._client.publish(
            self._topic,
            payload=make_payload(self._settings, status),
            qos=1,
            retain=True,
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.error("Failed to queue gateway status for publication")
        return info

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            self._connected.clear()
            LOGGER.error("MQTT connection refused: %s", reason_code)
            return
        self._connected.set()
        LOGGER.info("Gateway connected to MQTT broker")

    def _on_connect_fail(self, _client: mqtt.Client, _userdata: object) -> None:
        self._connected.clear()
        LOGGER.warning("MQTT connection attempt failed; retrying with backoff")

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        self._connected.clear()
        if not self._stop.is_set() and reason_code != 0:
            LOGGER.warning("MQTT connection lost; automatic reconnect is active")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    publisher = GatewayPublisher(settings)
    signal.signal(signal.SIGINT, publisher.stop)
    signal.signal(signal.SIGTERM, publisher.stop)
    publisher.run()


if __name__ == "__main__":
    main()
