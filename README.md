# LoRa MQTT Gateway Monitor

A small IoT monitoring application that lets a Raspberry Pi or other LoRa
gateway report its network IP and availability over MQTT. A Flask service
validates and stores the latest retained status, and a Vue dashboard presents
the current state of one or more gateways.

This repository contains two separate runtime roles:

- **Gateway publisher** — `mqtt_client.py`, deployed on every LoRa gateway.
- **Monitor service** — `app.py`, deployed with the web dashboard wherever the
  gateway state will be viewed.

The original prototype returned the Flask server's own IP and had an unrelated
publisher connected to a shared public topic. The current implementation joins
those pieces into a real MQTT data path.

## Architecture

```text
┌──────────────────────────┐       MQTT QoS 1        ┌─────────────────────┐
│ Raspberry Pi / gateway   │ ──────────────────────► │ Authenticated broker │
│ mqtt_client.py           │   retained status/LWT  │ TLS when remote      │
└──────────────────────────┘                         └──────────┬──────────┘
                                                              │ subscribe
                                                              ▼
┌──────────────────────────┐       same-origin API   ┌─────────────────────┐
│ Vue gateway dashboard    │ ◄────────────────────── │ Flask monitor       │
│ browser                  │   /api/gateways         │ app.py              │
└──────────────────────────┘                         └─────────────────────┘
```

Each gateway publishes to its own topic:

```text
lora/gateways/<gateway-id>/status
```

The monitor subscribes to:

```text
lora/gateways/+/status
```

## Features

- Multi-gateway IP, availability, and last-seen dashboard
- MQTT QoS 1 status messages and retained state
- Last Will and Testament (LWT) offline reporting
- Automatic reconnect with exponential backoff
- IPv4 and IPv6 validation
- Stale-device detection and old-message replay protection
- TLS, CA validation, username/password, and client-certificate support
- Device-specific topic naming suitable for broker ACL enforcement
- Bounded message size, JSON schema, gateway count, and identifier validation
- Same-origin Vue/Flask deployment with restrictive browser security headers
- Health and gateway APIs
- Systemd and Mosquitto configuration examples
- Backend tests plus frontend lint, build, and dependency audit commands

## Requirements

- Python 3.11 or newer
- Node.js 22.12 or newer (Node.js 24 LTS is recommended)
- An MQTT broker such as Mosquitto 2.x

The application was verified with Python 3.14, Node.js 24 LTS, Flask 3.1,
Paho MQTT 2.1, Vue 3.5, and Vite 8.

## Quick start: local development

This workflow keeps MQTT and HTTP bound to the same computer. Plaintext,
anonymous MQTT is only appropriate when the listener is restricted to
`127.0.0.1`.

### 1. Create the Python environment

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

The example configuration already selects `localhost:1883`. It also enables
the Flask MQTT subscriber.

### 2. Start a loopback-only broker

Create a temporary Mosquitto configuration outside the repository:

```text
listener 1883 127.0.0.1
allow_anonymous true
```

Then start Mosquitto with that file:

```bash
mosquitto -c /path/to/mosquitto-dev.conf -v
```

Do not change this listener to `0.0.0.0`; that would expose an anonymous,
unencrypted broker to the network.

### 3. Build the dashboard

```bash
cd lora-vue-frontend
npm ci
npm run build
cd ..
```

### 4. Start the monitor and simulated gateway

In one terminal:

```bash
python app.py
```

In a second terminal, using the same activated Python environment:

```bash
python mqtt_client.py
```

Open <http://127.0.0.1:5000>. The default publisher identifies itself as
`lora-gateway-01`.

For frontend hot reload, run `npm run dev` from `lora-vue-frontend` while Flask
is running. Vite proxies `/api` to Flask on port 5000.

## Configuration

Copy `.env.example` to `.env`. Real `.env` files and credentials are ignored by
Git.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MQTT_ENABLED` | `false` | Starts the MQTT subscriber inside the Flask monitor. |
| `MQTT_BROKER` | `localhost` | Broker hostname or IP; URL schemes are not accepted. |
| `MQTT_PORT` | `1883` local, `8883` remote | Broker TCP port. |
| `MQTT_TOPIC_PREFIX` | `lora/gateways` | Root topic without wildcards. |
| `MQTT_USERNAME` | unset | Broker user. Must be paired with `MQTT_PASSWORD`. |
| `MQTT_PASSWORD` | unset | Broker password. Never commit it. |
| `MQTT_TLS` | off for localhost, on for remote | Enables TLS and hostname verification. |
| `MQTT_CA_CERT` | system trust store | Optional private CA certificate. |
| `MQTT_CLIENT_CERT` | unset | Optional client certificate for mutual TLS. |
| `MQTT_CLIENT_KEY` | unset | Private key paired with the client certificate. |
| `MQTT_ALLOW_INSECURE_REMOTE` | `false` | Explicit exception for isolated test networks only. |
| `MQTT_CLIENT_ID` | generated by role | Optional fixed MQTT client ID. Do not share IDs. |
| `GATEWAY_ID` | `lora-gateway-01` | Device ID used in the MQTT topic and payload. |
| `GATEWAY_IP` | auto-detected | Explicit advertised IP when auto-detection is unsuitable. |
| `GATEWAY_PUBLISH_INTERVAL` | `60` | Online heartbeat interval in seconds. |
| `GATEWAY_STALE_SECONDS` | `180` | Age after which an online report becomes stale. |
| `MAX_GATEWAYS` | `100` | Memory bound for unique gateway records. |
| `HTTP_HOST` | `127.0.0.1` | Development HTTP bind address. |
| `HTTP_PORT` | `5000` | Development HTTP port. |
| `HTTP_TRUSTED_HOSTS` | local hosts | Comma-separated valid HTTP Host header values. |
| `HTTP_HSTS` | `false` | Enables HSTS; use only behind an HTTPS-only endpoint. |

Remote MQTT is rejected unless authentication is configured with either
username/password or a client certificate. Remote plaintext is also rejected
unless `MQTT_ALLOW_INSECURE_REMOTE=true` is deliberately set.

The gateway publisher and monitor can use different environment files. This is
recommended because their broker accounts require different permissions.

## MQTT message contract

An online status message has this exact JSON schema:

```json
{
  "schema_version": 1,
  "gateway_id": "lora-gateway-01",
  "ip": "192.168.1.42",
  "status": "online",
  "timestamp": "2026-07-17T09:30:00Z"
}
```

`status` is either `online` or `offline`. Offline LWT messages may use `null`
for the IP. Messages are retained and sent at QoS 1. The monitor rejects:

- payloads larger than 4096 bytes;
- malformed UTF-8 or JSON, including duplicate fields;
- unsupported or extra fields;
- invalid device IDs, IPs, states, or timestamps;
- a payload whose gateway ID does not match its MQTT topic;
- reports dated more than five minutes in the future;
- an older report that attempts to replace newer device state.

Gateway clocks must use NTP or another reliable time source.

## HTTP API

### `GET /api/health`

Returns process health, non-sensitive MQTT connection state, gateway count, and
server time. A disconnected configured broker is reported as `degraded` while
the endpoint remains reachable with HTTP 200 for monitoring systems.

### `GET /api/gateways`

Returns all known gateways in a stable ID order:

```json
{
  "gateways": [
    {
      "gateway_id": "lora-gateway-01",
      "ip": "192.168.1.42",
      "status": "online",
      "reported_status": "online",
      "last_seen": "2026-07-17T09:30:00Z",
      "received_at": "2026-07-17T09:30:00Z",
      "age_seconds": 2
    }
  ],
  "count": 1,
  "mqtt": {
    "enabled": true,
    "connected": true
  },
  "server_time": "2026-07-17T09:30:02Z"
}
```

### `GET /api/gateways/<gateway-id>`

Returns one gateway or `404 {"error":"gateway_not_found"}`.

### Legacy `GET /get-ip`

Temporarily retained for compatibility and marked deprecated in its response
headers. It now returns validated gateway data and never calculates or exposes
the Flask server's own IP. New clients must use `/api/gateways`.

All JSON responses use `Cache-Control: no-store`.

## Secure broker deployment

Examples are provided in `deploy/mosquitto.conf.example` and
`deploy/mosquitto.acl.example`.

Create separate users interactively so passwords do not appear in shell
history:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd monitor
sudo mosquitto_passwd /etc/mosquitto/passwd lora-gateway-01
```

The supplied ACL gives `monitor` read access to all status topics. A publisher's
broker username must match its `GATEWAY_ID`, and it can write only its own
status topic.

For any network connection beyond localhost:

1. Use a broker listener on port 8883 with a valid server certificate.
2. Give each gateway a unique credential or, preferably, a unique client
   certificate.
3. Apply the topic ACL and keep anonymous access disabled.
4. Store private keys and environment files outside the repository with
   operating-system permissions restricted to the service account.
5. Restrict the broker and web ports with host/network firewalls.
6. Rotate credentials and certificates when a gateway is retired or lost.

The sample Mosquitto files are templates; certificate paths and service users
must be adapted to the target host.

## Production web deployment

Build the dashboard first, then run Flask with a production WSGI server:

```bash
cd lora-vue-frontend
npm ci
npm run build
cd ..
waitress-serve --host=127.0.0.1 --port=5000 app:app
```

Keep Waitress on loopback and place an HTTPS reverse proxy in front of it. The
dashboard reveals internal IP addresses, so the reverse proxy should also
enforce authentication when the monitor is not limited to trusted operators.
Set `HTTP_TRUSTED_HOSTS` to the public hostname and enable `HTTP_HSTS=true` only
after HTTPS is enforced for every request.

Example systemd units are supplied in:

- `deploy/lora-gateway.service`
- `deploy/lora-monitor.service`

They assume the project is installed at `/opt/lora-mqtt`, the virtual
environment is `/opt/lora-mqtt/.venv`, and a restricted `lora` service account
exists. Review every path before installing them.

## Security audit summary

| Finding in the abandoned prototype | Resolution |
| --- | --- |
| Shared public EMQX broker and predictable topic | Defaults to localhost; per-gateway topic hierarchy and ACL template added. |
| Anonymous plaintext remote MQTT | Remote TLS and authentication enforced by configuration validation. |
| Flask bypassed MQTT and exposed its own host IP | Flask is now the MQTT subscriber; the API returns only validated gateway reports. |
| MQTT reconnect loop repeatedly started network threads | One Paho 2.x client per process with automatic exponential reconnect. |
| No device identity or message schema | Strict device ID, topic binding, JSON schema, IP, state, and time validation. |
| No offline detection | Retained heartbeat, LWT offline state, and stale timeout. |
| Old retained/replayed state could overwrite current state | Reports older than the stored timestamp are discarded. |
| Unbounded MQTT input/state | 4 KiB message limit and configurable gateway-count bound. |
| Wildcard browser CORS | Removed; UI and API use the same origin. |
| No browser hardening | CSP, frame denial, MIME sniffing prevention, referrer, permissions, and optional HSTS headers. |
| Unsafe/ambiguous SPA fallback | Safe path joining and JSON 404 behavior for unknown API routes. |
| Obsolete frontend toolchain with known dependency issues | Migrated from Vue CLI/Webpack to Vue 3.5 and Vite 8; current audit is clean. |
| Missing dependencies, tests, and deployment instructions | Pinned manifests, lockfile, 21 backend tests, broker templates, and service units added. |

### Remaining operational risks

No application can replace secure deployment controls. In particular:

- The in-memory monitor state is not historical storage. It is reconstructed
  from retained broker messages after restart.
- MQTT ACLs and user/certificate provisioning must be enforced by the broker.
- The Flask API does not implement user accounts. Use an authenticated reverse
  proxy if network users can reach it.
- IP addresses are operational data and may be sensitive in some environments.
- This project monitors gateway network presence; it does not validate LoRa
  radio payloads, LoRaWAN keys, firmware integrity, or secure boot.
- Production gateways still require OS patching, least-privilege service
  accounts, firewall rules, protected keys, log monitoring, and credential
  rotation.

## Verification

Backend:

```bash
python -m pytest -q
python -m ruff check .
python -m pip check
python -m pip_audit -r requirements.txt
```

Frontend:

```bash
cd lora-vue-frontend
npm ci
npm run lint
npm run build
npm audit --audit-level=high
```

## Repository layout

```text
.
├── app.py                         Flask API and frontend server
├── config.py                      validated environment configuration
├── mqtt_client.py                 gateway-side status publisher
├── mqtt_service.py                monitor subscriber and TLS setup
├── telemetry.py                   payload validation and gateway state
├── requirements.txt               runtime Python dependencies
├── requirements-dev.txt           test dependencies
├── tests/                          backend tests
├── deploy/                         Mosquitto and systemd templates
└── lora-vue-frontend/              Vue/Vite dashboard
```

## References

- [Eclipse Paho Python client documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/)
- [Flask production deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/)
- [Flask web security guidance](https://flask.palletsprojects.com/en/stable/web-security/)
- [OWASP IoT Security Verification Standard: communication requirements](https://owasp.org/IoT-Security-Verification-Standard-ISVS/en/V4-Communication_Requirements)

## License

MIT — see `LICENSE`.
