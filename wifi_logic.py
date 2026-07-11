import json
import random
import paho.mqtt.client as mqtt

# Konfigurasi HiveMQ
BROKER_IP = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC = "esp32/hr"

mqtt_client = None

def start_mqtt(callback_data, callback_log):
    global mqtt_client
    
    # 1. Pastikan Client ID unik agar tidak ditolak broker
    client_id = f"EDUSTRESS_BAND_{random.randint(1000, 9999)}"
    
    # 2. Inisialisasi Paho MQTT dengan kompatibilitas API
    try:
        # Versi terbaru paho-mqtt memerlukan CallbackAPIVersion
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    except AttributeError:
        # Fallback jika kamu menggunakan versi Paho MQTT yang lebih lama
        mqtt_client = mqtt.Client(client_id)
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            callback_log(f"Berhasil konek ke HiveMQ!")
            client.subscribe(TOPIC)
        else:
            callback_log(f"Gagal konek, error code: {rc}")

    def on_message(client, userdata, msg):
        try:
            print(f"DEBUG: Menerima paket MQTT! Ukuran: {len(msg.payload)} bytes")
            # 3. Decode pesan dari ESP32
            payload = msg.payload.decode()
            data = json.loads(payload)
            # Kirim data ke main.py
            callback_data(data)
        except Exception as e:
            callback_log(f"Error parse JSON: {e}")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # 4. Connect ke HiveMQ
    mqtt_client.connect(BROKER_IP, BROKER_PORT, 60)
    mqtt_client.loop_start()