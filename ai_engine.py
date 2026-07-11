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
        self.sample_counter = 0
        self.sample_index_buffer = []
        
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
        """Mengolah data IBI yang dikumpulkan menjadi nilai Baseline tetap."""

        # TAMBAHKAN DEBUG INI:
        print(f"DEBUG: Isi buffer kalibrasi saat ini: {len(self.calibration_ibi_buffer)} sampel")

        # 1. Validasi: Pastikan data cukup (misalnya minimal 50 detak)
        if len(self.calibration_ibi_buffer) < 50:
            logger.warning("Data kalibrasi tidak cukup!")
            return False

        # 2. Convert buffer ke numpy array untuk perhitungan cepat
        ibi_array = np.array(self.calibration_ibi_buffer)

        # 3. Hitung HR Baseline (Mean HR)
        # Rata-rata IBI = Mean(ibi_array)
        # HR = 60000 / Mean(IBI)
        mean_ibi = np.mean(ibi_array)
        self.hr_baseline = 60000.0 / mean_ibi

        # 4. Hitung RMSSD Baseline. RMSSD = akar kuadrat dari mean(selisih kuadrat IBI yang berurutan)
        diff_ibi = np.diff(ibi_array)
        self.rmssd_baseline = float(np.sqrt(np.mean(diff_ibi**2)))

        logger.info(f"Kalibrasi Berhasil! HR_Baseline: {self.hr_baseline}, RMSSD_Baseline: {self.rmssd_baseline}")
        return True

    def process_raw_signals(self, ppg_ir, ax, ay, az):
        self.sample_counter += 1
        self.ir_buffer.append(ppg_ir)
        self.sample_index_buffer.append(self.sample_counter)
        
        if len(self.ir_buffer) > 150: # Window size 150 untuk kestabilan
            self.ir_buffer.pop(0)
            self.sample_index_buffer.pop(0)

        if len(self.ir_buffer) >= 100:
            # --- TEKNIK SMOOTHING (Moving Average) ---
            # Menggunakan rolling average untuk menghilangkan noise frekuensi tinggi
            data_series = pd.Series(self.ir_buffer)
            ir_smooth = data_series.rolling(window=10).mean().fillna(0).values
            
            # Detrending
            ir_detrended = ir_smooth - np.mean(ir_smooth)
            
            # --- DETEKSI PUNCAK YANG LEBIH CERDAS ---
            # prominence dinaikkan agar hanya puncak yang "menonjol" yang dihitung
            peaks, _ = find_peaks(ir_detrended, distance=30, prominence=np.std(ir_detrended)*0.8)

            if len(peaks) >= 2:
                # Ambil 2 puncak terakhir
                idx1 = self.sample_index_buffer[peaks[-2]]
                idx2 = self.sample_index_buffer[peaks[-1]]
                
                ibi = (idx2 - idx1) * 16.67 

                if 400 < ibi < 1500:
                    self.last_ibi = ibi
                    self.last_hr = 60000.0 / ibi
                    
                    # Simpan ke buffer kalibrasi jika aktif
                    if self.is_calibrating:
                        # Hitung HR sementara untuk validasi (60000/ibi)
                        temp_hr = 60000.0 / ibi
                        if 40 < temp_hr < 150:
                            self.calibration_ibi_buffer.append(ibi)
                            print(f"DEBUG: Data HR {temp_hr:.2f} diterima (Buffer: {len(self.calibration_ibi_buffer)})")
                        else:
                            # Log jika ada data dibuang
                            logger.warning(f"Data HR {temp_hr:.2f} dibuang (Outlier).")
                        print(f"DEBUG: Puncak ditemukan! HR: {self.last_hr:.2f}, Buffer count: {len(self.calibration_ibi_buffer)}")
                else:
                    self.last_hr = 0.0
            else:
                self.last_hr = 0.0

        return float(self.last_hr), float(self.last_ibi), float(np.sqrt(ax**2 + ay**2 + az**2))

    def extract_features(self, current_hr, current_rmssd, task_level, rmssd_trend):
        try:
            if self.hr_baseline is None or self.rmssd_baseline is None:
                return 0.0

            # 1. RUMUS DELTA & LOAD INDEX
            delta_hr = current_hr - self.hr_baseline
            delta_rmssd = current_rmssd - self.rmssd_baseline
            load_index = task_level * rmssd_trend
            
            # 2. Persiapkan fitur (Pastikan urutan ini SAMA PERSIS dengan saat training!)
            feature_cols = ['delta_hr', 'delta_rmssd', 'task_level', 'load_index']
            
            # Pastikan data dalam bentuk float yang bersih
            features_data = np.array([[float(delta_hr), float(delta_rmssd), float(task_level), float(load_index)]])
            
            # 3. Prediksi
            scaled_features = self.scaler.transform(features_data)
            prediction = self.model.predict(scaled_features)
            
            return float(prediction[0])
            
        except Exception as e:
            logger.error(f"AI_ERROR: {e}")
            return 0.0 # Default Normal jika error

    def calculate_current_rmssd(self):
        """Menghitung RMSSD dari buffer real-time."""
        if len(self.ibi_buffer) < 2: return 30.0
        diff_ibi = np.diff(self.ibi_buffer)
        return float(np.sqrt(np.mean(diff_ibi**2)))