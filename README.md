# LoRa-MQTT IP Request Application

Welcome to the **LoRa-MQTT IP Request Application**! 🚀 This project integrates a **Flask** backend with a **Vue.js** frontend to request and display the IP address of a **LoRa gateway** on a **Raspberry Pi** using the **MQTT protocol**.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Contributing](#contributing)
- [License](#license)

## Overview

This application is designed to simplify the process of obtaining and displaying the IP address of a LoRa gateway. By combining the power of **Flask** and **Vue.js**, the app ensures seamless communication between the Raspberry Pi, the gateway, and the user interface.

The app serves as both an IP address provider (via the Flask API) and a frontend dashboard (Vue.js) that allows users to request and display the IP of the LoRa gateway.

## Features

✨ **Real-time IP Address Retrieval**: Quickly fetch the current IP address of the LoRa gateway connected to the Raspberry Pi.

💻 **Integrated Frontend and Backend**: Vue.js frontend and Flask backend are bundled into one application, all served from the same port for simplicity.

📡 **MQTT Protocol**: The app uses MQTT to ensure efficient, lightweight communication between devices.

🎨 **User-friendly Interface**: Vue.js ensures a modern, responsive interface for interacting with the app.

⚙️ **Modular Design**: Clean separation of frontend and backend code, making it easy to extend and modify.

## Project Structure

```bash
LoRa-MQTT/
├── app.py                      # Flask backend - serves API and frontend
├── mqtt_client.py              # MQTT client to request LoRa gateway IP
├── lora-vue-frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── App.vue         # Main Vue component
│   │   │   ├── RequestIP.vue   # Vue component for IP address requests
│   ├── dist/                   # Built Vue.js frontend
│   └── (other Vue files)
└── README.md                   # Project documentation
