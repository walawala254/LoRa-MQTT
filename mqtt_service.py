"""MQTT subscriber and shared secure-client configuration."""

from __future__ import annotations

import logging
import threading
import uuid

import paho.mqtt.client as mqtt

from config import GATEWAY_ID_PATTERN, Settings
from telemetry import GatewayStore, TelemetryError, parse_telemetry


LOGGER = logging.getLogger(__name__)


def configure_client(client: mqtt.Client, settings: Settings) -> None:
    if settings.mqtt_username and settings.mqtt_password:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(
            ca_certs=settings.mqtt_ca_cert,
            certfile=settings.mqtt_client_cert,
            keyfile=settings.mqtt_client_key,
        )
        client.tls_insecure_set(False)
    client.reconnect_delay_set(min_delay=1, max_delay=120)


class MqttSubscriber:
    def __init__(self, settings: Settings, store: GatewayStore) -> None:
        self._settings = settings
        self._store = store
        self._connected = threading.Event()
        self._started = False
        client_id = settings.mqtt_client_id or f"lora-monitor-{uuid.uuid4().hex[:12]}"
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        configure_client(self._client, settings)
        self._client.on_connect = self._on_connect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._client.connect_async(
            self._settings.mqtt_broker,
            self._settings.mqtt_port,
            keepalive=60,
        )
        self._client.loop_start()
        LOGGER.info("MQTT subscriber started")

    def stop(self) -> None:
        if not self._started:
            return
        self._client.disconnect()
        self._client.loop_stop()
        self._started = False
        self._connected.clear()

    def status(self) -> dict[str, bool]:
        return {"started": self._started, "connected": self._connected.is_set()}

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            self._connected.clear()
            LOGGER.error("MQTT connection refused: %s", reason_code)
            return
        topic = f"{self._settings.mqtt_topic_prefix}/+/status"
        result, _message_id = client.subscribe(topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.error("Unable to subscribe to the gateway status topic")
            return
        self._connected.set()
        LOGGER.info("MQTT subscriber connected")

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
        if self._started and reason_code != 0:
            LOGGER.warning("MQTT connection lost; automatic reconnect is active")

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        topic_prefix = f"{self._settings.mqtt_topic_prefix}/"
        if not message.topic.startswith(topic_prefix) or not message.topic.endswith("/status"):
            return
        gateway_id = message.topic[len(topic_prefix) : -len("/status")]
        if not GATEWAY_ID_PATTERN.fullmatch(gateway_id):
            LOGGER.warning("Discarded MQTT message with invalid gateway topic")
            return
        try:
            telemetry = parse_telemetry(message.payload, gateway_id)
        except TelemetryError as exc:
            LOGGER.warning("Discarded invalid MQTT telemetry: %s", exc)
            return
        if not self._store.update(telemetry):
            LOGGER.warning("Discarded replayed telemetry or gateway state beyond capacity")
