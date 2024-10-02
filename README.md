
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
```

## Setup Instructions

### Prerequisites

Before setting up the project, ensure that you have the following installed on your system:

- Python 3.x (for Flask)
- Node.js (for Vue.js frontend)
- Git (for version control)
- Mosquitto MQTT Broker (if you don’t have an MQTT broker installed)

### Step 1: Clone the Repository

```bash
git clone https://github.com/walawala254/LoRa-MQTT.git
cd LoRa-MQTT
```

### Step 2: Backend Setup (Flask)

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

Start the Flask backend:

```bash
python app.py
```

### Step 3: Frontend Setup (Vue.js)

Navigate to the Vue frontend directory:

```bash
cd lora-vue-frontend
```

Install the Vue.js dependencies:

```bash
npm install
```

Build the production-ready Vue app:

```bash
npm run build
```

The Vue app will now be built and placed in the `dist` folder.

### Step 4: Running the Full Application

The Flask app will serve the built Vue frontend, making everything available from one port. To start the entire application, simply run:

```bash
python app.py
```

Now, open your browser and visit:

```bash
http://localhost:5000
```

You'll see the Vue frontend, and you can request the LoRa gateway's IP!

## Running the Application

To run the Flask app from the LoRa-MQTT directory:

```bash
python app.py
```

Open your browser and go to:

```bash
http://localhost:5000
```

Interact with the dashboard to request the IP address of the LoRa gateway via MQTT!

## Contributing

We welcome contributions to make this project even better! Feel free to submit a pull request or open an issue if you encounter any bugs or have ideas for enhancements.

To contribute:

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request for review.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Thank you for using the LoRa-MQTT IP Request Application! 😊
