import logging
logger = logging.getLogger(__name__)

import pandas as pd
import numpy as np
import joblib
import os
import time
from scipy.signal import find_peaks
import scipy.stats as stats
from scipy.signal import welch
import nolds

class AIEngine:
    def __init__(self, model_name, scaler_name):
        base_path = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_path, "models", model_name)
        scaler_path = os.path.join(base_path, "models", scaler_name)
        self.sample_counter = 0
        self.sample_index_buffer = []

        self.feature_baseline = None
        
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
        if len(self.calibration_ibi_buffer) < 50:
            return False

        # 1. Hitung baseline HR & RMSSD (seperti biasa)
        ibi_array = np.array(self.calibration_ibi_buffer)
        mean_ibi = np.mean(ibi_array)
        self.hr_baseline = 60000.0 / mean_ibi
        self.rmssd_baseline = float(np.sqrt(np.mean(np.diff(ibi_array)**2)))

        # 2. HITUNG BASELINE 4 FITUR ML
        # Kita hitung fitur dari seluruh data kalibrasi yang terkumpul
        self.feature_baseline = self.calculate_4_features(ibi_array)
        
        logger.info(f"Kalibrasi Berhasil! Baseline Fitur: {self.feature_baseline}")
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
                    if len(self.ibi_buffer) > 600: # Simpan window 30 detak
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

    def calculate_4_features(self, ibi_data):
        """
        Murni untuk ekstraksi fitur. 
        Input: array IBI (RR-Interval)
        Output: [DFA2, ApEn, VLF, LF/HF]
        """
        if len(ibi_data) < 60:  # Minimal 60 poin data agar aman untuk DFA
            return None
        
        # 1. FFT dengan Welch Method
        freqs, psd = welch(ibi_data, fs=1, nperseg=len(ibi_data))
        
        # 2. Hitung Power
        vlf_pow = np.sum(psd[(freqs >= 0.003) & (freqs <= 0.04)])
        lf_pow = np.sum(psd[(freqs >= 0.04) & (freqs <= 0.15)])
        hf_pow = np.sum(psd[(freqs >= 0.15) & (freqs <= 0.4)])
        
        vlf_log = np.log(vlf_pow + 1e-6)
        lf_hf = (lf_pow / hf_pow) if hf_pow > 0 else 0
        
        # 3. ApEn
        def apen(u, m=2, r=0.2):
            def _phi(m):
                x = np.array([u[i:i+m] for i in range(len(u) - m + 1)])
                C = np.sum(np.max(np.abs(x[:, np.newaxis] - x), axis=2) <= r*np.std(u), axis=0) / len(u)
                return np.sum(np.log(C + 1e-6)) / len(u)
            return _phi(m) - _phi(m+1)

        apen_val = apen(ibi_data)
        
        # 4. DFA2
        import nolds
        try:
            dfa2_val = nolds.dfa(ibi_data, nvals=range(12, min(50, len(ibi_data) // 2)))
        except:
            dfa2_val = 0.0 # Nilai cadangan jika gagal
        
        # Hanya mengembalikan list angka
        return [float(dfa2_val), float(apen_val), float(vlf_log), float(lf_hf)]

    def extract_features(self, current_hr, current_rmssd, ax, ay, az):
        try:
            # Pastikan baseline sudah ada (HR, RMSSD, dan 4 Fitur ML)
            if self.hr_baseline is None or self.rmssd_baseline is None or self.feature_baseline is None:
                return None

            motion_level, magnitude = self.get_motion_level(ax, ay, az)
            if motion_level == 2:
                logger.info(f"Data Rejected: High Motion (Mag: {magnitude:.2f})")
                return None 

            # 1. Delta HR & RMSSD (Safety Override)
            delta_hr = current_hr - self.hr_baseline
            delta_rmssd = current_rmssd - self.rmssd_baseline
            
            # 2. Delta ML Features
            ml_features = self.calculate_4_features(np.array(self.ibi_buffer))
            if ml_features is None: return None
            
            # RUMUS DELTA: Realtime - Baseline
            ml_delta = [ml_features[i] - self.feature_baseline[i] for i in range(4)]
            
            return {
                "delta_hr": float(delta_hr),
                "delta_rmssd": float(delta_rmssd),
                "motion_level": motion_level,
                "ml_delta": ml_delta # Mengirim data yang sudah di-Delta
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
        # 0-1000: Diam/Sangat tenang (Data bersih)
        # 1000-4000: Gerakan ringan (Acceptable)
        # >4000: Gerakan tinggi (Reject)
        if deviation < 1000:
            return 0, magnitude
        elif deviation < 4000:
            return 1, magnitude
        else:
            return 2, magnitude
        
    # --- UTILITY ---
    def calculate_current_rmssd(self):
        # Tetap simpan untuk kalkulasi safety metrics di atas
        if len(self.ibi_buffer) < 2: return 30.0 
        diff_ibi = np.diff(self.ibi_buffer)
        if np.std(diff_ibi) == 0: return 30.0
        return float(np.sqrt(np.mean(diff_ibi**2)))