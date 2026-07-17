# LoRa Gateway Monitor frontend

Vue 3 and Vite frontend for the LoRa MQTT Gateway Monitor. The complete setup,
security model, deployment instructions, and API contract are documented in
the repository root `README.md`.

```bash
npm ci
npm run dev       # development server; proxies /api to Flask on port 5000
npm run lint
npm run build     # production output in dist/
npm audit --audit-level=high
```

Node.js 22.12 or newer is required. Node.js 24 LTS is recommended.
