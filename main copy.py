import flet as ft
import threading
import time
import json
import numpy as np
from datetime import datetime
import paho.mqtt.client as mqtt
import wifi_logic
import traceback

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
# logging.getLogger("paho").setLevel(logging.WARNING)

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
        self._add_log_message("Menyalakan mesin MQTT otomatis...")
        
        # 1. Validasi user
        if not self.active_user: 
            self._add_log_message("Error: User tidak ditemukan!")
            return

        # 2. Reset Status (State Machine)
        self.is_calibrating = True
        self.ai.is_calibrating = True
        self.is_calibrated = False
        self.calibration_seconds = 180
        self.calibration_hr_samples = []
        self.has_received_first_data = False
        
        logging.info("Menunggu aliran data dari Gelang IoT...")

        # 3. Menjalankan MQTT Gateway satu-satunya
        # Kita menggunakan lambda agar bisa mengirim argumen ke wifi_logic.start_mqtt
        threading.Thread(
            target=lambda: wifi_logic.start_mqtt(self.on_local_message, self._add_log_message), 
            daemon=True
        ).start()

    def on_local_message(self, data):
        try:
            batch_list = data.get('data', [])
            
            for item in batch_list:
                ppg_ir = int(item.get("ir", 0))
                red_val = int(item.get("red", 0))
                ax = float(item.get("ax", 0))
                ay = float(item.get("ay", 0))
                az = float(item.get("az", 0))
                
                if ppg_ir == 0: continue

                # 1. LOG RAW SENSOR (Wajib untuk visualisasi)
                # OPTIMASI: Jangan log setiap 16ms (60Hz) jika database keberatan.
                # Jika terasa lambat, kamu bisa log hanya setiap sampel ke-5 atau ke-10.
                if self.db:
                    self.db.add_raw_sensor_log(self.active_user['id'], ppg_ir, red_val, ax, ay, az, 0, 0, 0)

                # 2. TRIGGER TIMER PERTAMA (Hanya jalan sekali)
                if not getattr(self, 'has_received_first_data', False):
                    self.has_received_first_data = True
                    # Pastikan status diinisialisasi
                    self.is_calibrating = True
                    self.is_calibrated = False
                    self.calibration_seconds = 180
                    threading.Thread(target=self.start_calibration_timer, daemon=True).start()

                # 3. PROSES DSP (Menghitung HR, IBI, Acc)
                hr, ibi, acc = self.ai.process_raw_signals(ppg_ir, ax, ay, az)

                # 4. DISPATCHER
                if self.is_calibrating:
                    if 40 < hr < 180:
                        self.record_calibration_sample(hr, ax, ay, az)
                    
                elif self.is_calibrated:
                    # Pastikan update_ai_prediction() sudah menangani logika database kesehatan
                    self.update_ai_prediction()

        except Exception as e: 
            print(f"Error pada on_local_message: {e}")

    def start_calibration_timer(self):
        logging.info("Memulai countdown kalibrasi...")
        
        # 1. Inisialisasi State yang Aman
        self.calibration_seconds = 180
        self.is_calibrating = True
        self.is_calibrated = False
        
        try:
            # 2. Loop Utama dengan monitoring state
            while self.is_calibrating and self.calibration_seconds > 0:
                time.sleep(1) # Interval 1 detik
                self.calibration_seconds -= 1
                
                # Update UI dengan proteksi
                if self.dashboard:
                    self.dashboard.update_calibration_ui(self.calibration_seconds, total_seconds=180)
                    self.page.update()
                
                logging.debug(f"Sisa waktu kalibrasi: {self.calibration_seconds} detik")

            # 3. Kondisi Selesai Normal
            if self.calibration_seconds <= 0:
                logging.info("Waktu kalibrasi habis, memanggil finalize...")
                self.finalize_calibration()
                
        except Exception as e:
            logging.error(f"Timer crash: {e}", exc_info=True)
            self._add_log_message("Error: Kalibrasi terhenti mendadak.")
            self.is_calibrating = False
        
        finally:
            # 4. Pastikan UI selalu update status terakhir
            if self.dashboard and self.dashboard.status_ref.current:
                status_color = "green" if self.is_calibrated else "red"
                status_text = "NORMAL" if self.is_calibrated else "FAILED"
                self.dashboard.status_ref.current.value = status_text
                self.dashboard.status_ref.current.color = status_color
            self.page.update()

    def record_calibration_sample(self, hr, ax, ay, az):
        # 1. Hitung magnitudo akselerasi (Vector Sum)
        acc_magnitude = (ax**2 + ay**2 + az**2)**0.5
        
        # Threshold gerakan (Sesuaikan nilainya sesuai sensitivitas sensor MPU6050)
        # Jika acc_magnitude terlalu tinggi, berarti user bergerak -> data kotor
        MOVEMENT_THRESHOLD = 15000 
        
        if acc_magnitude > MOVEMENT_THRESHOLD:
            # Data kotor, abaikan sample ini agar baseline tidak terkontaminasi
            self._add_log_message("Gerakan terdeteksi! Mengabaikan sample...")
            return 

        # 2. Jika bersih, baru simpan ke list
        self.calibration_hr_samples.append(hr)
        
        # 3. Simpan log (Opsional)
        if self.db:
            self.db.add_calibration_log(self.active_user['id'], hr, hr * 0.45)
        
        # 4. Update UI
        try: self._update_health_ui(int(hr), calibrating=True)
        except: pass

    def finalize_calibration(self):

        # Kita cetak siapa yang memanggil fungsi ini
        print("--- [DEBUG] finalize_calibration dipanggil oleh: ---")
        traceback.print_stack() 
        print("------------------------------------------------------")
        
        # Jangan biarkan lanjut jika waktu belum habis (di bawah 175 detik sebagai toleransi)
        if self.calibration_seconds > 5: 
            logging.warning(f"Finalisasi ditolak! Detik tersisa masih: {self.calibration_seconds}")
            return
    
        if self.ai.calculate_baseline():
            
            # 2. Simpan ke Tabel 
            success = self.db.save_calibration_result(
                user_id=self.active_user['id'], 
                hr_baseline=float(self.ai.hr_baseline),
                rmssd_baseline=float(self.ai.rmssd_baseline)
            )
            
            if success:
                print("DEBUG: Final Baseline tersimpan ke database!")
            
            # 3. Ubah Status
            self.is_calibrating = False
            self.is_calibrated = True
            self._add_log_message("Kalibrasi Selesai! Baseline Terkunci.")
        else:
            self._add_log_message("Error: Gagal menghitung baseline.")

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