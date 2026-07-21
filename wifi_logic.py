import json
import random
import ssl
import paho.mqtt.client as mqtt

# ============================
# Konfigurasi HiveMQ Cloud
# ============================
BROKER_IP = "3199ba06d24f4cd0aeda42d9a9f1533c.s1.eu.hivemq.cloud"
BROKER_PORT = 8883

# Credential sesuai tabel: server_edustress (Publish and Subscribe) -> dipakai Laptop (APK Fleet)
MQTT_USERNAME = "server_edustress"
MQTT_PASSWORD = "edustress123"  # isi sesuai yang di-set di HiveMQ Cloud Console

# Topic sesuai tabel "Topic Filter yang diisi"
TOPIC_SUB_WRISTBAND = "edustress/wristband/data"     # subscribe - data dari wristband
TOPIC_SUB_ENVIRONMENT = "edustress/environment/data" # subscribe - data dari custom box (env)
TOPIC_PUB_FATIGUE = "edustress/fatigue/result"        # publish - hasil deteksi fatigue (dari model XGBoost)
TOPIC_PUB_CONTROL = "edustress/control/command"       # publish - perintah kontrol kipas/lampu

mqtt_client = None


def start_mqtt(callback_data, callback_log):
    global mqtt_client

    # 1. Client ID unik agar tidak ditolak broker
    client_id = f"EDUSTRESS_LAPTOP_{random.randint(1000, 9999)}"

    # 2. Inisialisasi Paho MQTT dengan kompatibilitas API
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    except AttributeError:
        mqtt_client = mqtt.Client(client_id)

    # 3. WAJIB untuk HiveMQ Cloud: set username/password
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # 4. WAJIB untuk HiveMQ Cloud: aktifkan TLS di port 8883
    mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            callback_log("Berhasil konek ke HiveMQ Cloud!")
            # Subscribe ke dua topic sesuai role server_edustress
            client.subscribe([
                (TOPIC_SUB_WRISTBAND, 0),
                (TOPIC_SUB_ENVIRONMENT, 0),
            ])
            callback_log(f"Subscribed: {TOPIC_SUB_WRISTBAND}, {TOPIC_SUB_ENVIRONMENT}")
        else:
            callback_log(f"Gagal konek, error code: {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)
            print(f"DEBUG: Pesan diterima dari topic '{msg.topic}', {len(msg.payload)} bytes")

            # Bedakan sumber data berdasarkan topic
            if msg.topic == TOPIC_SUB_WRISTBAND:
                data["_source"] = "wristband"
            elif msg.topic == TOPIC_SUB_ENVIRONMENT:
                data["_source"] = "environment"

            # Kirim data ke main.py / logic APK
            callback_data(data)
        except Exception as e:
            callback_log(f"Error parse JSON dari topic {msg.topic}: {e}")

    def on_disconnect(client, userdata, rc):
        callback_log(f"Terputus dari broker (rc={rc}), mencoba reconnect...")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    # 5. Connect ke HiveMQ Cloud
    mqtt_client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
    mqtt_client.loop_start()


def publish_fatigue_result(result: dict):
    """Publish hasil deteksi fatigue (output model XGBoost: Normal/Fatigue)."""
    if mqtt_client is None:
        return
    mqtt_client.publish(TOPIC_PUB_FATIGUE, json.dumps(result), qos=0)


def publish_control_command(command: dict):
    """Publish perintah kontrol aktuator (misal: {"fan": "on", "lamp": "off"})."""
    if mqtt_client is None:
        return
    mqtt_client.publish(TOPIC_PUB_CONTROL, json.dumps(command), qos=0)


def stop_mqtt():
    if mqtt_client is not None:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()