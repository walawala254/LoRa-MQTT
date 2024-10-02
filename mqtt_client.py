import paho.mqtt.client as mqtt
import socket
import time

# MQTT setup
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "lora_gateway/ip"

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Error getting IP address: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully to broker")
        ip_address = get_ip_address()
        if ip_address:
            client.publish(MQTT_TOPIC, ip_address)
            print(f"Published IP: {ip_address} to topic {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from broker")

def connect_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            time.sleep(5)
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds.")
            time.sleep(5)

if __name__ == "__main__":
    connect_mqtt()
