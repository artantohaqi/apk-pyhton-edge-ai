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
        self.ibi_buffer = []  
        self.ir_buffer = []
        self.time_buffer = []
        self.last_hr = 75.0
        self.last_ibi = 0.0

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
        
        if len(self.ir_buffer) > 150:
            self.ir_buffer.pop(0)
            self.sample_index_buffer.pop(0)

        if len(self.ir_buffer) >= 100:
            data_series = pd.Series(self.ir_buffer)
            ir_smooth = data_series.rolling(window=10).mean().fillna(0).values
            ir_detrended = ir_smooth - np.mean(ir_smooth)
            
            peaks, _ = find_peaks(ir_detrended, distance=30)
            
            if len(peaks) >= 2:
                idx1 = self.sample_index_buffer[peaks[-2]]
                idx2 = self.sample_index_buffer[peaks[-1]]
                ibi = (idx2 - idx1) * 16.67 

                if 400 < ibi < 1500:
                    self.last_ibi = ibi
                    self.last_hr = 60000.0 / ibi
                    
                    # --- PERBAIKAN: INJEKSI DATA DINAMIS ---
                    self.ibi_buffer.append(float(ibi))
                    if len(self.ibi_buffer) > 30: # Simpan window 30 detak
                        self.ibi_buffer.pop(0)
                    
                    if self.is_calibrating:
                        temp_hr = 60000.0 / ibi
                        if 40 < temp_hr < 150:
                            self.calibration_ibi_buffer.append(ibi)
                else:
                    self.last_hr = 0.0
            else:
                self.last_hr = 0.0

        return float(self.last_hr), float(self.last_ibi), float(np.sqrt(ax**2 + ay**2 + az**2))

    def extract_features(self, current_hr, current_rmssd, ax, ay, az):
        try:
            if self.hr_baseline is None or self.rmssd_baseline is None:
                return None

            # 1. Gating/Filtering berdasarkan Motion
            motion_level, magnitude = self.get_motion_level(ax, ay, az)
            
            if motion_level == 2:
                logger.info(f"Data Rejected: High Motion Detected (Mag: {magnitude:.2f})")
                return None # Mengembalikan None jika data terlalu berisik

            # 2. RUMUS DELTA
            delta_hr = current_hr - self.hr_baseline
            delta_rmssd = current_rmssd - self.rmssd_baseline
            
            # 3. Persiapkan fitur (hanya delta_hr, delta_rmssd, motion_level)
            features_data = np.array([[float(delta_hr), float(delta_rmssd), float(motion_level)]])
            
            # Kembalikan data yang sudah di-gating untuk dikirim ke sistem/database
            return {
                "delta_hr": float(delta_hr),
                "delta_rmssd": float(delta_rmssd),
                "motion_level": motion_level
            }
            
        except Exception as e:
            logger.error(f"AI_ERROR: {e}")
            return None

    def get_motion_level(self, ax, ay, az):
        """
        Menentukan level gerakan berdasarkan magnitude akselerometer.
        Asumsi MPU6050: 1g = ~16384.
        """
        # Hitung magnitude vektor
        magnitude = np.sqrt(ax**2 + ay**2 + az**2)
        
        # Hitung deviasi dari gaya gravitasi bumi (1g = 16384)
        # Jika nilai magnitude terlalu jauh dari 16384, artinya ada gerakan/guncangan
        deviation = abs(magnitude - 16384)
        
        # Threshold:
        # 0-3000: Diam/Sangat tenang (Data bersih)
        # 3000-8000: Gerakan ringan (Acceptable)
        # >8000: Gerakan tinggi (Reject)
        if deviation < 3000:
            return 0, magnitude
        elif deviation < 8000:
            return 1, magnitude
        else:
            return 2, magnitude
        
    def calculate_current_rmssd(self):
        """Menghitung RMSSD dari buffer yang sudah terupdate real-time."""
        # Jika data belum cukup, kembalikan nilai 0 atau baseline
        if len(self.ibi_buffer) < 2: 
            return 30.0 
        
        # Hitung selisih antar detak (RR-Interval/IBI)
        diff_ibi = np.diff(self.ibi_buffer)
        
        # Validasi agar tidak menghitung RMSSD dari data yang sama (jika std=0)
        if np.std(diff_ibi) == 0:
            return 30.0
            
        rmssd = np.sqrt(np.mean(diff_ibi**2))
        return float(rmssd)