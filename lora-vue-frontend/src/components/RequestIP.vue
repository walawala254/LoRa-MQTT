<template>
  <div>
    <h2>LoRa Gateway IP Address</h2>
    <button @click="requestIP">Get IP Address</button>
    <p v-if="ipAddress">IP: {{ ipAddress }}</p>
  </div>
</template>

<script>
export default {
  data() {
    return {
      ipAddress: ''
    }
  },
  methods: {
    async requestIP() {
      try {
        const response = await fetch('/get-ip');  // Relative path since Flask and Vue are on the same server
        const data = await response.json();
        this.ipAddress = data.ip;
      } catch (error) {
        console.error("Failed to get IP address.", error);
      }
    }
  }
}
</script>
