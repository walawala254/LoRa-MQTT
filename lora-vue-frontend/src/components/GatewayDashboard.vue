<template>
  <main class="page-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">
          LoRa operations
        </p>
        <h1>Gateway monitor</h1>
        <p class="subtitle">
          Live network identity and availability reported over MQTT.
        </p>
      </div>
      <div
        class="broker-state"
        :class="brokerClass"
      >
        <span
          class="state-dot"
          aria-hidden="true"
        />
        {{ brokerLabel }}
      </div>
    </header>

    <section
      class="toolbar"
      aria-label="Gateway summary"
    >
      <div class="summary">
        <span class="summary-value">{{ gateways.length }}</span>
        <span class="summary-label">{{ gateways.length === 1 ? 'gateway' : 'gateways' }}</span>
      </div>
      <div class="summary">
        <span class="summary-value online-count">{{ onlineCount }}</span>
        <span class="summary-label">online</span>
      </div>
      <button
        class="refresh-button"
        type="button"
        :disabled="loading"
        @click="loadGateways"
      >
        <span
          :class="{ spinning: loading }"
          aria-hidden="true"
        >↻</span>
        {{ loading ? 'Refreshing' : 'Refresh' }}
      </button>
    </section>

    <p
      v-if="error"
      class="notice error"
      role="alert"
    >
      <strong>Dashboard unavailable.</strong> {{ error }}
    </p>

    <section
      v-if="!loading && !error && gateways.length === 0"
      class="empty-state"
    >
      <div
        class="empty-icon"
        aria-hidden="true"
      >
        ⌁
      </div>
      <h2>Waiting for gateway telemetry</h2>
      <p>
        Start the gateway publisher and confirm it uses the same broker and topic prefix.
      </p>
    </section>

    <section
      v-else-if="gateways.length"
      class="gateway-grid"
      aria-live="polite"
    >
      <article
        v-for="gateway in gateways"
        :key="gateway.gateway_id"
        class="gateway-card"
      >
        <div class="card-header">
          <div>
            <p class="card-label">
              Gateway
            </p>
            <h2>{{ gateway.gateway_id }}</h2>
          </div>
          <span
            class="status-pill"
            :class="`status-${gateway.status}`"
          >
            <span
              class="state-dot"
              aria-hidden="true"
            />
            {{ gateway.status }}
          </span>
        </div>

        <dl class="details">
          <div class="detail-primary">
            <dt>IP address</dt>
            <dd>{{ gateway.ip || 'Not reported' }}</dd>
          </div>
          <div>
            <dt>Last report</dt>
            <dd>{{ relativeTime(gateway.last_seen) }}</dd>
          </div>
          <div>
            <dt>Reported at</dt>
            <dd>{{ formatDate(gateway.last_seen) }}</dd>
          </div>
        </dl>
      </article>
    </section>

    <footer>
      <span>Automatic refresh every {{ refreshSeconds }} seconds</span>
      <span v-if="lastUpdated">Dashboard updated {{ relativeTime(lastUpdated) }}</span>
    </footer>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const refreshSeconds = 10
const gateways = ref([])
const mqtt = ref({ enabled: false, connected: false })
const loading = ref(true)
const error = ref('')
const lastUpdated = ref('')
let refreshTimer

const onlineCount = computed(
  () => gateways.value.filter((gateway) => gateway.status === 'online').length,
)

const brokerLabel = computed(() => {
  if (!mqtt.value.enabled) return 'MQTT disabled'
  return mqtt.value.connected ? 'Broker connected' : 'Broker disconnected'
})

const brokerClass = computed(() => {
  if (!mqtt.value.enabled) return 'state-disabled'
  return mqtt.value.connected ? 'state-online' : 'state-offline'
})

async function loadGateways() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/gateways', {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`The server returned HTTP ${response.status}.`)
    const data = await response.json()
    if (!Array.isArray(data.gateways) || typeof data.mqtt !== 'object') {
      throw new Error('The server returned an unexpected response.')
    }
    gateways.value = data.gateways
    mqtt.value = data.mqtt
    lastUpdated.value = new Date().toISOString()
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : 'Request failed.'
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  if (!value) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'medium',
  }).format(new Date(value))
}

function relativeTime(value) {
  if (!value) return 'never'
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000)
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  if (Math.abs(seconds) < 60) return formatter.format(seconds, 'second')
  const minutes = Math.round(seconds / 60)
  if (Math.abs(minutes) < 60) return formatter.format(minutes, 'minute')
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return formatter.format(hours, 'hour')
  return formatter.format(Math.round(hours / 24), 'day')
}

onMounted(() => {
  loadGateways()
  refreshTimer = window.setInterval(loadGateways, refreshSeconds * 1000)
})

onBeforeUnmount(() => window.clearInterval(refreshTimer))
</script>

<style>
:root {
  color: #17211d;
  background: #eef3ef;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background:
    radial-gradient(circle at 8% 5%, rgba(81, 151, 112, 0.16), transparent 24rem),
    linear-gradient(135deg, #f6f8f6 0%, #e8efea 100%);
}

button {
  font: inherit;
}

.page-shell {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
  padding: 72px 0 36px;
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 32px;
  margin-bottom: 40px;
}

.eyebrow,
.card-label {
  margin: 0 0 8px;
  color: #31714e;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #12231b;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2.8rem, 7vw, 5.4rem);
  font-weight: 500;
  letter-spacing: -0.055em;
  line-height: 0.98;
}

.subtitle {
  max-width: 620px;
  margin: 22px 0 0;
  color: #5c6c64;
  font-size: 1.05rem;
  line-height: 1.65;
}

.broker-state,
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  flex: 0 0 auto;
  padding: 10px 14px;
  border: 1px solid #cfdbd3;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: #526259;
  font-size: 0.82rem;
  font-weight: 700;
}

.state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 14%, transparent);
}

.state-online,
.status-online {
  color: #187447;
}

.state-offline,
.status-offline {
  color: #b64236;
}

.state-disabled,
.status-stale {
  color: #9a6819;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 36px;
  margin-bottom: 24px;
  padding: 18px 20px;
  border: 1px solid rgba(190, 206, 196, 0.8);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.58);
  box-shadow: 0 16px 50px rgba(28, 53, 40, 0.05);
  backdrop-filter: blur(12px);
}

.summary {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.summary-value {
  color: #172b21;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.75rem;
}

.online-count {
  color: #187447;
}

.summary-label {
  color: #718078;
  font-size: 0.83rem;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-left: auto;
  padding: 10px 16px;
  border: 0;
  border-radius: 10px;
  background: #1d5037;
  color: white;
  cursor: pointer;
  font-weight: 700;
  transition: transform 160ms ease, background 160ms ease;
}

.refresh-button:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #153e2a;
}

.refresh-button:focus-visible {
  outline: 3px solid rgba(32, 118, 72, 0.32);
  outline-offset: 3px;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.spinning {
  animation: spin 800ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.notice,
.empty-state {
  border: 1px solid #d7c9c5;
  border-radius: 18px;
  background: rgba(255, 250, 248, 0.8);
}

.notice {
  padding: 18px 20px;
  color: #8c342d;
}

.empty-state {
  padding: 72px 24px;
  text-align: center;
}

.empty-icon {
  color: #448763;
  font-size: 3.5rem;
}

.empty-state h2 {
  margin: 12px 0 8px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.8rem;
  font-weight: 500;
}

.empty-state p {
  max-width: 520px;
  margin: auto;
  color: #68776f;
  line-height: 1.6;
}

.gateway-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
  gap: 20px;
}

.gateway-card {
  position: relative;
  overflow: hidden;
  padding: 28px;
  border: 1px solid rgba(190, 206, 196, 0.9);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 55px rgba(29, 57, 42, 0.07);
}

.gateway-card::before {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, #2c8053, #b8d4c2);
  content: "";
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-header h2 {
  margin: 0;
  color: #1c2b24;
  font-size: 1.25rem;
  overflow-wrap: anywhere;
}

.status-pill {
  padding: 7px 11px;
  font-size: 0.72rem;
  text-transform: capitalize;
}

.details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
  margin: 32px 0 0;
}

.details div {
  min-width: 0;
}

.details .detail-primary {
  grid-column: 1 / -1;
  padding-bottom: 22px;
  border-bottom: 1px solid #e1e8e3;
}

dt {
  margin-bottom: 7px;
  color: #77857e;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

dd {
  margin: 0;
  color: #36443d;
  font-size: 0.88rem;
  overflow-wrap: anywhere;
}

.detail-primary dd {
  color: #173928;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: clamp(1.25rem, 4vw, 1.8rem);
}

footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 28px;
  color: #78867e;
  font-size: 0.75rem;
}

@media (max-width: 640px) {
  .page-shell {
    width: min(100% - 28px, 1120px);
    padding-top: 38px;
  }

  .hero {
    display: block;
  }

  .broker-state {
    margin-top: 24px;
  }

  .toolbar {
    flex-wrap: wrap;
    gap: 20px;
  }

  .refresh-button {
    width: 100%;
    justify-content: center;
    margin-left: 0;
  }

  .gateway-card {
    padding: 22px;
  }

  footer {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
