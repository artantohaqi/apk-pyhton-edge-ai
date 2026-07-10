import logging
logger = logging.getLogger(__name__)

import pandas as pd
import numpy as np
import joblib
import os
import time
from scipy.signal import find_peaks

class AIEngine:
    def __init__(self, model_name, scaler_name):
        base_path = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_path, "models", model_name)
        scaler_path = os.path.join(base_path, "models", scaler_name)
        
        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.status_msg = "AI Engine: Active"
        except Exception as e:
            self.status_msg = f"AI Error: {str(e)}"
            
        # --- BUFFER REAL-TIME (Untuk Smoothing/DSP) ---
        self.ibi_buffer = [800.0] * 30  
        self.ir_buffer = []
        self.time_buffer = []
        self.last_hr = 75.0
        self.last_ibi = 800.0

        # --- BUFFER & VARIABEL BASELINE (KALIBRASI 3 MENIT) ---
        self.is_calibrating = False
        self.calibration_ibi_buffer = [] 
        self.hr_baseline = None
        self.rmssd_baseline = None

    def start_calibration(self):
        """Memulai sesi rekam baseline selama 3 menit."""
        self.calibration_ibi_buffer = []
        self.is_calibrating = True
        logger.info("Sesi Kalibrasi dimulai (3 menit).")

    def calculate_baseline(self):
        """Mengolah 3 menit data IBI menjadi nilai Baseline tetap."""
        if len(self.calibration_ibi_buffer) < 50:
            logger.warning("Data kalibrasi tidak cukup!")
            return False
            
        # Hitung HR Baseline
        self.hr_baseline = 60000.0 / np.mean(self.calibration_ibi_buffer)
        
        # Hitung RMSSD Baseline
        diff_ibi = np.diff(self.calibration_ibi_buffer)
        self.rmssd_baseline = np.sqrt(np.mean(diff_ibi**2))
        
        self.is_calibrating = False
        logger.info(f"Kalibrasi Selesai! Baseline: HR={self.hr_baseline:.2f}, RMSSD={self.rmssd_baseline:.2f}")
        return True

    def process_raw_signals(self, ppg_ir, ax, ay, az):
        """DSP Engine: Mencari detak jantung & mengisi buffer."""
        
        # 1. Kalkulasi MPU6050 (Hitung sekali di awal)
        calculated_acc = np.sqrt(ax**2 + ay**2 + az**2)
        
        # Simpan sebagai class attribute agar aman diakses
        self.last_acc = calculated_acc 
        
        # 2. Masukkan data IR ke memori sementara (Buffer)
        current_time = time.time()
        self.ir_buffer.append(ppg_ir)
        self.time_buffer.append(current_time)

        if len(self.ir_buffer) > 100:
            self.ir_buffer.pop(0)
            self.time_buffer.pop(0)

        # 3. DSP ENGINE: Mencari Detak Jantung
        # Hanya jalan jika data cukup
        if len(self.ir_buffer) >= 50:
            ir_detrended = np.array(self.ir_buffer) - np.mean(self.ir_buffer)
            # Hitung peaks
            peaks, _ = find_peaks(ir_detrended, distance=10, prominence=np.std(ir_detrended)*0.5)

            if len(peaks) >= 2:
                t1 = self.time_buffer[peaks[-2]]
                t2 = self.time_buffer[peaks[-1]]
                ibi = (t2 - t1) * 1000.0

                # Validasi medis
                if 400 < ibi < 1500:
                    self.last_ibi = ibi
                    self.last_hr = 60000.0 / ibi
                    
                    # Jika kalibrasi aktif, simpan data ke buffer baseline
                    if self.is_calibrating:
                        self.calibration_ibi_buffer.append(ibi)

        # 4. Update Buffer Fitur AI (Rolling window 60 detik)
        self.ibi_buffer.append(self.last_ibi)
        if len(self.ibi_buffer) > 60: 
            self.ibi_buffer.pop(0)
        
        # 5. RETURN PASTI (3 NILAI)
        # Fungsi ini sekarang dijamin mengembalikan 3 nilai: HR, IBI, dan Acc
        return float(self.last_hr), float(self.last_ibi), float(calculated_acc)

    def extract_features(self, current_hr, current_rmssd, task_level, rmssd_trend):
        """
        Model baru harus menerima Delta dan Load Index, bukan angka mentah.
        """
        try:
            if self.hr_baseline is None or self.rmssd_baseline is None:
                return 0.0 # Belum kalibrasi

            # 1. RUMUS DELTA & LOAD INDEX (Sesuai paper)
            delta_hr = current_hr - self.hr_baseline
            delta_rmssd = current_rmssd - self.rmssd_baseline
            load_index = task_level * rmssd_trend
            
            # 2. Persiapkan fitur (sesuaikan dengan urutan retraining kamu nanti!)
            # Urutan di sini harus SAMA PERSIS dengan saat kamu training di notebook
            feature_cols = ['delta_hr', 'delta_rmssd', 'task_level', 'load_index']
            
            features_df = pd.DataFrame([[
                float(delta_hr), float(delta_rmssd), float(task_level), float(load_index)
            ]], columns=feature_cols)
            
            # 3. Prediksi
            scaled_features = self.scaler.transform(features_df)
            prediction = self.model.predict(scaled_features)
            
            return float(prediction[0])
            
        except Exception as e:
            logger.error(f"AI_ERROR: {e}")
            return 0.0

    def calculate_current_rmssd(self):
        """Menghitung RMSSD dari buffer real-time."""
        if len(self.ibi_buffer) < 2: return 30.0
        diff_ibi = np.diff(self.ibi_buffer)
        return float(np.sqrt(np.mean(diff_ibi**2)))