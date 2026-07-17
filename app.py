"""Flask API and static frontend for the LoRa gateway monitor."""

from __future__ import annotations

import atexit
from datetime import UTC, datetime
import logging
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, send_from_directory
from werkzeug.security import safe_join

from config import Settings
from mqtt_service import MqttSubscriber
from telemetry import GatewayStore


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "lora-vue-frontend" / "dist"


def create_app(
    settings: Settings | None = None,
    *,
    start_mqtt: bool | None = None,
) -> Flask:
    """Create the application without forcing network access during tests."""
    settings = settings or Settings.from_env()
    # Static files are served by the validated SPA fallback below. Disabling
    # Flask's automatic static route prevents it from swallowing unknown APIs.
    app = Flask(__name__, static_folder=None)
    app.config.update(
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=16 * 1024,
        TRUSTED_HOSTS=settings.http_trusted_hosts,
    )

    store = GatewayStore(
        stale_after_seconds=settings.gateway_stale_seconds,
        max_gateways=settings.max_gateways,
    )
    subscriber = MqttSubscriber(settings, store)
    app.extensions["gateway_store"] = store
    app.extensions["mqtt_subscriber"] = subscriber

    should_start_mqtt = settings.mqtt_enabled if start_mqtt is None else start_mqtt
    if should_start_mqtt:
        subscriber.start()
        atexit.register(subscriber.stop)

    @app.after_request
    def add_security_headers(response: Any) -> Any:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'; object-src 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        if settings.http_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if response.content_type and response.content_type.startswith("application/json"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health() -> tuple[Any, int]:
        mqtt_status = subscriber.status()
        ready = not settings.mqtt_enabled or mqtt_status["connected"]
        body = {
            "status": "ok" if ready else "degraded",
            "ready": ready,
            "mqtt": {
                "enabled": settings.mqtt_enabled,
                "connected": mqtt_status["connected"],
            },
            "gateway_count": store.count,
            "server_time": _utc_now(),
        }
        return jsonify(body), 200

    @app.get("/api/gateways")
    def gateways() -> Any:
        records = store.snapshots()
        return jsonify(
            {
                "gateways": records,
                "count": len(records),
                "mqtt": {
                    "enabled": settings.mqtt_enabled,
                    "connected": subscriber.status()["connected"],
                },
                "server_time": _utc_now(),
            }
        )

    @app.get("/api/gateways/<gateway_id>")
    def gateway(gateway_id: str) -> tuple[Any, int] | Any:
        record = store.snapshot(gateway_id)
        if record is None:
            return jsonify({"error": "gateway_not_found"}), 404
        return jsonify(record)

    @app.get("/get-ip")
    def legacy_get_ip() -> tuple[Any, int]:
        """Keep the old route temporarily without returning the server's own IP."""
        records = store.snapshots()
        if not records:
            response = jsonify(
                {
                    "error": "gateway_not_available",
                    "message": "No gateway telemetry has been received.",
                }
            )
            response.headers["Deprecation"] = "true"
            response.headers["Link"] = '</api/gateways>; rel="successor-version"'
            return response, 503

        response = jsonify(
            {
                "ip": records[0]["ip"],
                "gateway_id": records[0]["gateway_id"],
                "status": records[0]["status"],
            }
        )
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = '</api/gateways>; rel="successor-version"'
        return response, 200

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def serve_frontend(path: str) -> tuple[Any, int] | Any:
        if not FRONTEND_DIST.is_dir():
            return (
                jsonify(
                    {
                        "error": "frontend_not_built",
                        "message": "Run `npm install` and `npm run build` in lora-vue-frontend.",
                    }
                ),
                503,
            )

        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "not_found"}), 404

        safe_path = safe_join(str(FRONTEND_DIST), path) if path else None
        requested = Path(safe_path) if safe_path else None
        if path and requested and requested.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    return app


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    runtime_settings = Settings.from_env()
    app.run(
        host=runtime_settings.http_host,
        port=runtime_settings.http_port,
        debug=False,
    )
