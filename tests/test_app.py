from __future__ import annotations

from flask.testing import FlaskClient

from app import create_app
from config import Settings
from telemetry import GatewayTelemetry


def make_client(settings: Settings) -> FlaskClient:
    application = create_app(settings, start_mqtt=False)
    application.config["TESTING"] = True
    return application.test_client()


def test_health_and_security_headers(settings: Settings) -> None:
    response = make_client(settings).get("/api/health")

    assert response.status_code == 200
    assert response.json["ready"] is True
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_gateway_api_returns_validated_store_data(
    settings: Settings,
    online_telemetry: GatewayTelemetry,
) -> None:
    application = create_app(settings, start_mqtt=False)
    application.config["TESTING"] = True
    application.extensions["gateway_store"].update(online_telemetry)

    response = application.test_client().get("/api/gateways")

    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["gateways"][0]["gateway_id"] == "gateway-01"
    assert response.json["gateways"][0]["status"] == "online"


def test_unknown_gateway_returns_json_404(settings: Settings) -> None:
    response = make_client(settings).get("/api/gateways/unknown")

    assert response.status_code == 404
    assert response.json == {"error": "gateway_not_found"}


def test_unknown_api_route_does_not_fall_through_to_frontend(settings: Settings) -> None:
    response = make_client(settings).get("/api/not-a-real-route")

    assert response.status_code == 404
    assert response.json == {"error": "not_found"}


def test_legacy_ip_route_does_not_expose_server_ip(settings: Settings) -> None:
    response = make_client(settings).get("/get-ip")

    assert response.status_code == 503
    assert response.json["error"] == "gateway_not_available"
    assert response.headers["Deprecation"] == "true"
