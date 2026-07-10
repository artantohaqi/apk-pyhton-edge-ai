import flet as ft
import threading
import time
import json
import numpy as np
from datetime import datetime
import paho.mqtt.client as mqtt

from database import DBManager
from ai_engine import AIEngine
from views.auth_view import AuthView
from views.dashboard_view import DashboardView
from views.screentime_view import ScreentimeView
from views.hr_log_view import HRLogView

import logging
import sys

# Konfigurasi sekali saja di main.py untuk seluruh aplikasi
logger = logging.getLogger() # Logger root
logger.setLevel(logging.INFO)

# Handler file
file_handler = logging.FileHandler("app_debug.log", mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Handler terminal
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)

# Ini akan menangkap log dari main, database, dan ai_engine
# 4. Tes logging (Ini harus muncul di file jika berhasil)
logger.info("====== SISTEM LOGGING DIMULAI ======")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log"), # Log akan disimpan di sini
        logging.StreamHandler()              # Log tetap muncul di terminal (hanya INFO ke atas)
    ]
)
# Ubah level logging Flet agar tidak spam terminal
logging.getLogger("flet").setLevel(logging.WARNING) 
logging.getLogger("paho").setLevel(logging.WARNING)

class FatigueApp:
    def __init__(self, page: ft.Page):
        logging.info("====== BOOTING START ======")
        self.page = page
        self.db = DBManager()
        self.ai = AIEngine("model_xgboost_fatigue.pkl", "scaler_fatigue.pkl")

        self.current_web_level = "Level 1"
        self.web_seconds = 0
        self.cum_physical_activity = 0.0  
        self.status = "NORMAL"
        self.active_user = None 
        self.rmssd_history = []
        
        self.is_calibrated = False           
        self.calibration_seconds = 180      
        self.is_calibrating = False
        self.calibration_start_time = None
        self.calibration_timer = 0
        self.current_task_level = 0        
        self.calibration_hr_samples = []    
        self.has_received_first_data = False

        self.dashboard = None
        self.log_view = None
        self.screentime_view = None
        
        self.page.clean()
        self.page.add(AuthView(self.db, self.on_login_success))
        self.is_task_active = False

        for handler in logging.getLogger().handlers:
            handler.flush()
        logging.info("====== BOOTING COMPLETE ======")

    def on_login_success(self, user_data):
        self.active_user = user_data
        logging.info(f"OK Sesi User Terkunci -> User: {self.active_user['username']}")

        self.dashboard = DashboardView(self.ai.status_msg, self.on_connect_click)
        self.setup_main_page()
        
        # 1. FIX: Update UI Profil 
        try:
            self.dashboard.update_profile_ui(self.active_user)
            self.page.update()
        except Exception as e:
            logging.error(f"Update profil ui error (Abaikan jika tetap muncul): {e}")

        # 2. FIX FATAL: Otomatis jalankan MQTT saat masuk Dashboard
        logging.info("Menyalakan mesin MQTT otomatis...")
        threading.Thread(target=lambda: self.on_connect_click(None), daemon=True).start()
        
    def setup_main_page(self):
        self.page.title = "Edge AI MQTT System"
        self.page.theme_mode = ft.ThemeMode.DARK 
        self.page.clean()
        
        nav_options = [ft.dropdown.Option("Home"), ft.dropdown.Option("Logout")]
        self.nav = ft.Dropdown(
            value="Home", width=200, bgcolor=ft.Colors.GREY_800, 
            color=ft.Colors.WHITE, options=nav_options
        )
        
        self.container = ft.Container(content=self.dashboard, expand=True)
        self.page.add(
            ft.Row([
                ft.Text("AIoT MQTT System Dashboard", size=16, weight="bold", color=ft.Colors.BLUE_400), 
                self.nav
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_700),
            self.container
        )
        self.page.update()

    def on_connect_click(self, e):
        if not self.active_user: return
        self.is_calibrating = True
        self.is_calibrated = False
        self.calibration_seconds = 180
        self.calibration_hr_samples = []
        self.has_received_first_data = False
        
        logging.info("Menunggu aliran data dari Gelang IoT...")
        threading.Thread(target=self.start_mqtt_local, daemon=True).start()
        threading.Thread(target=self.start_mqtt_public, daemon=True).start()

    def start_calibration_timer(self):
        logging.info("Data masuk! Memulai countdown kalibrasi...")
        while getattr(self, 'is_calibrating', False) and not getattr(self, 'is_calibrated', False):
            if self.calibration_seconds > 0:
                self.calibration_seconds -= 1
                if self.dashboard:
                    self.dashboard.update_calibration_ui(self.calibration_seconds, total_seconds=180)
                self.page.update()
                time.sleep(1)
            else:
                self.is_calibrated = True
                self.is_calibrating = False
                self._add_log_message("Kalibrasi Selesai! Mengunci Baseline.")
                if self.dashboard and self.dashboard.status_ref.current:
                    self.dashboard.status_ref.current.value = "NORMAL"
                    self.dashboard.status_ref.current.color = "green"
                self.page.update()
                break

    def start_mqtt_local(self):
        client_id = f"EDUSTRESS_BAND_{int(time.time())}"
        try:
            self.mqtt_local = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        except AttributeError:
            self.mqtt_local = mqtt.Client(client_id)
            
        self.mqtt_local.on_connect = lambda c, u, f, rc: self._add_log_message("Port 1883 Terbuka! Terhubung ke HiveMQ Gelang.")
        self.mqtt_local.on_message = self.on_local_message
        self.mqtt_local.connect("broker.hivemq.com", 1883, 60)
        self.mqtt_local.subscribe("esp32/hr", qos=1)
        self.mqtt_local.loop_forever()

    def on_local_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode()
            
            # 1. FILTER ANTI-CRASH JIKA BUKAN JSON
            if not payload_str.strip().startswith("{"):
                return
            
            data = json.loads(payload_str)
            ppg_ir = int(data.get("ir", 0))
            red_val = int(data.get("red", 0))
            ax = float(data.get("ax", 0))
            ay = float(data.get("ay", 0))
            az = float(data.get("az", 0))
            
            if ppg_ir == 0: return

            # 2. TRIGGER TIMER PERTAMA KALI
            if not getattr(self, 'has_received_first_data', False):
                self.has_received_first_data = True
                threading.Thread(target=self.start_calibration_timer, daemon=True).start()

            # 3. SIMPAN KE DATABASE RAW SENSOR
            if self.db:
                self.db.add_raw_sensor_log(self.active_user['id'], ppg_ir, red_val, ax, ay, az, 0, 0, 0)

            # 4. PROSES AI
            hr, ibi, acc = self.ai.process_raw_signals(ppg_ir, ax, ay, az)
            self.cum_physical_activity += acc
            
            if getattr(self, 'is_calibrating', False):
                self.calibration_hr_samples.append(hr)
                if self.db:
                    self.db.add_calibration_log(self.active_user['id'], hr, hr * 0.45)
                self._update_health_ui(int(hr), calibrating=True)
                
            elif getattr(self, 'is_calibrated', False):
                # 1. Ambil data current
                current_rmssd = self.ai.calculate_current_rmssd()
                
                # 2. Update histori RMSSD untuk hitung trend
                self.rmssd_history.append(current_rmssd)
                if len(self.rmssd_history) > 5:
                    self.rmssd_history.pop(0)
                rmssd_trend = float(np.diff(self.rmssd_history).mean()) if len(self.rmssd_history) > 1 else 0.0

                # 3. Panggil AI Engine
                task_level = float(getattr(self, 'current_task_level', 1.0))
                
                pred = self.ai.extract_features(
                    current_hr=float(hr),
                    current_rmssd=float(current_rmssd),
                    task_level=task_level,
                    rmssd_trend=float(rmssd_trend)
                )

                # 4. Logika Status
                if pred == 2: self.status = "DIGITAL FATIGUE"
                elif pred == 1: self.status = "STRESS"
                else: self.status = "NORMAL"

                # 5. AMAN DARI ERROR: Log ke Database
                # Kita gunakan default 0.0 jika baseline masih None (meskipun seharusnya tidak mungkin)
                base_hr = self.ai.hr_baseline if self.ai.hr_baseline is not None else hr
                base_rmssd = self.ai.rmssd_baseline if self.ai.rmssd_baseline is not None else current_rmssd
                
                delta_hr = float(hr - base_hr)
                delta_rmssd = float(current_rmssd - base_rmssd)

                if self.db:
                    self.db.add_health_metrics_log(
                        self.active_user['id'], 
                        hr, ibi, acc, 
                        delta_hr, 
                        delta_rmssd, 
                        self.status
                    )

                self._update_health_ui(int(hr), calibrating=False)
                
        except Exception as e: 
            print(f"Error pemrosesan data: {e}")

    def start_mqtt_public(self):
        try:
            client_id = f"PUB_LARAVEL_{int(time.time())}"
            try:
                self.mqtt_public = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
            except AttributeError:
                self.mqtt_public = mqtt.Client(client_id)
                
            self.mqtt_public.on_message = self.on_public_message
            self.mqtt_public.on_connect = lambda c, u, f, rc, p=None: self._add_log_message("Terhubung ke Public Broker (Laravel ready)!")
            self.mqtt_public.connect("broker.hivemq.com", 1883, 60)
            self.mqtt_public.subscribe("polines/fatigue/web")
            self.mqtt_public.loop_start()
        except Exception as e:
            print(f"Public MQTT Error: {e}")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            raw_payload = msg.payload.decode()
            data = json.loads(raw_payload)
            
            # 1. PENGOLAHAN DATA MENTAH
            result = self.ai.process_raw_signals(
                data.get('ir', 0), data.get('ax', 0), data.get('ay', 0), data.get('az', 0)
            )
            
            if not isinstance(result, (list, tuple)) or len(result) != 3:
                return
            hr, ibi, acc = result
            
            # 2. LOGIKA KALIBRASI
            if self.is_calibrating:
                if self.calibration_start_time is None:
                    self.calibration_start_time = time.time()
                
                elapsed_time = time.time() - self.calibration_start_time
                
                if elapsed_time >= 180:
                    if self.ai.calculate_baseline():
                        # 1. Pastikan baseline tidak None
                        if self.ai.hr_baseline is not None and self.ai.rmssd_baseline is not None:
                            print("DEBUG: Mencoba menyimpan baseline ke database...")
                            
                            # 2. Panggil fungsi database
                            # Gunakan self.active_user['id'] yang biasa kamu pakai di kode lain
                            success = self.db.save_calibration_result(
                                user_id=self.active_user['id'], 
                                hr_baseline=float(self.ai.hr_baseline),
                                rmssd_baseline=float(self.ai.rmssd_baseline)
                            )
                            
                            if success:
                                print("DEBUG: Data berhasil masuk ke tabel calibration_results!")
                            else:
                                print("DEBUG: Gagal menyimpan data ke database.")
                        else:
                            print("DEBUG: Baseline masih kosong (None), gagal simpan.")
                        
                        self.is_calibrating = False
                        self.is_calibrated = True
                        self.show_snack("Kalibrasi Berhasil!")
                    else:
                        print("DEBUG: calculate_baseline gagal.")
                        self.show_snack("Kalibrasi Gagal!")
                    
                    self.calibration_start_time = None
            
            # 3. LOGIKA PREDIKSI
            elif self.is_calibrated:
                self.update_ai_prediction()

            self.data_queue.put(data)
                
        except Exception as e:
            # Menggunakan exc_info=True sangat penting untuk melihat error di DB
            logging.error(f"Error pada on_mqtt_message: {e}", exc_info=True)

    def on_public_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self.current_web_level = data.get("level", "Level 1")
            self.web_seconds = int(data.get("duration_seconds", 0))
            if self.dashboard: 
                if self.dashboard.web_level_ref.current:
                    self.dashboard.web_level_ref.current.value = f"Sedang Mengerjakan: {self.current_web_level}"
                if self.dashboard.web_timer_ref.current:
                    self.dashboard.web_timer_ref.current.value = f"Stopwatch Eksperimen: {self.web_seconds}s"
                self.page.update()
        except: pass

    def _update_health_ui(self, hr_val, calibrating=False):
        if self.dashboard and self.dashboard.hr_ref.current:
            self.dashboard.hr_ref.current.value = f"{hr_val} BPM"
            if not calibrating and self.dashboard.status_ref.current:
                self.dashboard.status_ref.current.value = self.status
                if self.status == "DIGITAL FATIGUE": self.dashboard.status_ref.current.color = "red"
                elif self.status == "STRESS": self.dashboard.status_ref.current.color = "orange"
                else: self.dashboard.status_ref.current.color = "green"
            self.page.update()

    def _add_log_message(self, message):
        if self.dashboard and self.dashboard.log_ref.current:
            self.dashboard.log_ref.current.controls.append(ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] {message}"))
            if len(self.dashboard.log_ref.current.controls) > 15: 
                self.dashboard.log_ref.current.controls.pop(0)
            self.page.update()
    
    # Di main.py, dalam fungsi _db_worker
    def _db_worker(self):
        while True:
            data = self.data_queue.get()
            try:
                # Tambahkan LOG agar tahu proses berjalan
                # logging.info(f"DB_WORKER: Menyimpan data ke database. Antrean saat ini: {self.data_queue.qsize()}")
                self.db.execute_query(
                    "INSERT INTO performa_logs (ir, red, ax, ay, az) VALUES (%s, %s, %s, %s, %s)",
                    (data['ir'], data['red'], data['ax'], data['ay'], data['az'])
                )
            except Exception as e:
                logging.error(f"DB Worker Error: {e}")
            finally:
                self.data_queue.task_done()

    # Di dalam class FatigueApp di main.py, bagian update_ai_prediction:
    def update_ai_prediction(self):
        try:
            # 1. Pastikan baseline sudah ada
            if self.ai.hr_baseline is None or self.ai.rmssd_baseline is None:
                return

            # 2. Ambil data current dari AI Engine
            current_hr = self.ai.last_hr
            current_rmssd = self.ai.calculate_current_rmssd()
            
            # 3. Hitung Trend (Perbandingan rmssd saat ini dengan baseline)
            # Menghindari pembagian dengan nol
            rmssd_trend = (current_rmssd / self.ai.rmssd_baseline) if self.ai.rmssd_baseline > 0 else 1.0
            
            # 4. Panggil AI Engine dengan 4 ARGUMEN EKSKLUSIF
            pred = self.ai.extract_features(
                current_hr=float(current_hr),
                current_rmssd=float(current_rmssd),
                task_level=float(self.current_task_level),
                rmssd_trend=float(rmssd_trend)
            )
            
            # 5. Logika Status
            if pred == 2:
                self.status = "DIGITAL FATIGUE"
                self.trigger_mitigation()
            elif pred == 1:
                self.status = "STRESS"
            else:
                self.status = "NORMAL"
                
            logging.info(f"[TRACE] Prediksi: {self.status} (Raw: {pred})")
            
        except Exception as e:
            logging.error(f"Error update_ai_prediction: {e}", exc_info=True)

if __name__ == "__main__":
    ft.app(target=FatigueApp)