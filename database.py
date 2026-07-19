import mysql.connector
from datetime import datetime
import threading
import logging
logger = logging.getLogger(__name__)


class DBManager:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'skripsi'
        }
        self.lock = threading.Lock()
        self.is_connected = False
        
        try:
            conn = self.get_connection()
            conn.close()
            logger.info("* Database connection test PASSED")
            self.is_connected = True
            self.create_tables()
        except Exception as e:
            logger.error(" Database connection test FAILED: %s", str(e))
            self.is_connected = False

    def get_connection(self):
        return mysql.connector.connect(
            host=self.config['host'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database']
        )

    def create_tables(self):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            with self.lock:
                # 1. Tabel Registrasi Profil User
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) UNIQUE,
                        email VARCHAR(100) UNIQUE, 
                        password VARCHAR(255),
                        age INT, 
                        bb FLOAT, 
                        tb FLOAT, 
                        kelamin_id INT, 
                        role VARCHAR(20) DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 2. Tabel Pendukung Sensor IoT
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS raw_sensor_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
                        ppg_ir INT, ppg_red INT, ax FLOAT, ay FLOAT, az FLOAT, gx FLOAT, gy FLOAT, gz FLOAT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calibration_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
                        hr FLOAT, rmssd FLOAT, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calibration_results (
                        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, hr_baseline FLOAT,rmssd_baseline FLOAT, dfa2_baseline FLOAT, apen_baseline FLOAT, vlf_baseline FLOAT,lfhf_baseline FLOAT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_metrics_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
                        hr FLOAT, rmssd FLOAT, delta_hr FLOAT, delta_rmssd FLOAT, motion_level INT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS screentime (
                        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
                        app_name VARCHAR(255), start_time DATETIME, duration INT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS window_slicing_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY, 
                        user_id INT,
                        start_time DATETIME, 
                        end_time DATETIME, 
                        avg_delta_hr FLOAT, 
                        avg_delta_rmssd FLOAT,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)

                # 3. Tabel untuk Prediction Logs (Hasil Analisis Tren)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY, 
                        window_id INT,
                        prediction_status VARCHAR(50), 
                        trend_score FLOAT, 
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (window_id) REFERENCES window_slicing_logs(id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
                logger.info("* Skema tabel database skripsi berhasil diperbarui!")

            # --- AUTO-SEED ADMIN ---
            with self.lock:
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                admin_exist = cursor.fetchone()
                
                if not admin_exist:
                    logger.info("⚠️ Akun Admin belum terdeteksi. Melakukan auto-seeding...")
                    query_admin = """
                        INSERT INTO users (username, email, password, age, kelamin_id, tb, bb, role) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query_admin, ('admin', 'admin@polines.ac.id', 'admin123', 22, 1, 170.0, 65.0, 'admin'))
                    conn.commit()
                    logger.info("🎉 Akun Admin default berhasil disuntikkan!")

        except Exception as e:
            logger.error(" Gagal membuat skema tabel: %s", str(e))
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ========================================================
    # FIX FATAL 1: FUNGSI INI KEMARIN HILANG (BUAT DATA MENTAH)
    # ========================================================
    def add_raw_sensor_log(self, user_id, ppg_ir, ppg_red, ax, ay, az, gx, gy, gz):
        if not self.is_connected or user_id is None: return False
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """INSERT INTO raw_sensor_logs 
                       (user_id, ppg_ir, ppg_red, ax, ay, az, gx, gy, gz) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (user_id, ppg_ir, ppg_red, float(ax), float(ay), float(az), float(gx), float(gy), float(gz)))
            conn.commit()
            return True
            logger.info("Database berhasil terhubung!")
        except Exception as e:
            logger.error(" Error insert raw log: %s", str(e))
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def add_calibration_log(self, user_id, hr, rmssd):
        if not self.is_connected or user_id is None: return False
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO calibration_logs (user_id, hr, rmssd) VALUES (%s, %s, %s)"
            cursor.execute(query, (user_id, float(hr), float(rmssd)))
            conn.commit()
            return True
        except Exception as e:
            logger.error(" Error insert calibration log: %s", str(e))
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def save_calibration_result(self, user_id, hr_baseline, rmssd_baseline, feature_baseline):
        # feature_baseline adalah list: [dfa2, apen, vlf, lfhf]
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """INSERT INTO calibration_results 
                    (user_id, hr_baseline, rmssd_baseline, dfa2_baseline, apen_baseline, vlf_baseline, lfhf_baseline) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            
            cursor.execute(query, (
                user_id, float(hr_baseline), float(rmssd_baseline), 
                float(feature_baseline[0]), float(feature_baseline[1]), 
                float(feature_baseline[2]), float(feature_baseline[3])
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving calibration: {e}")
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ========================================================
    # FIX FATAL 2: FUNGSI KEMBAR DIHAPUS, SISA 1 YANG BENAR
    # ========================================================
    # Di dalam database.py
    def add_health_metrics(self, user_id, hr, rmssd, delta_hr, delta_rmssd, motion_level):
        # Sesuaikan dengan nama kolom di tabel health_metrics_logs kamu
        query = """INSERT INTO health_metrics_logs 
                (user_id, hr, rmssd, delta_hr, delta_rmssd, motion_level, timestamp) 
                VALUES (%s, %s, %s, %s, %s, %s, NOW())"""
        
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            with self.lock:
                cursor.execute(query, (user_id, hr, rmssd, delta_hr, delta_rmssd, motion_level))
                conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Gagal simpan ke health_metrics_logs: {e}")
        finally:
            if conn:
                conn.close()

    # ========================================================
    # FIX FATAL 3: PENYESUAIAN NAMA KOLOM (recorded_at & status_ai)
    # ========================================================
    def get_all_health_logs(self, user_id):
        if not self.is_connected or user_id is None: return []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            # Ubah timestamp jadi recorded_at, status jadi status_ai
            query = "SELECT recorded_at, hr, ibi, acc, status_ai FROM health_metrics_logs WHERE user_id = %s ORDER BY recorded_at DESC LIMIT 50"
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Error fetching health logs: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def register_user(self, username, email, password, age, kelamin_id, tb, bb):
        if not self.is_connected: return False, "Database Terputus"
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            with self.lock:
                query = """INSERT INTO users (username, email, password, age, kelamin_id, tb, bb) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (username, email, password, age, kelamin_id, tb, bb))
                conn.commit()
            return True, "Registrasi Berhasil"
        except mysql.connector.Error as err:
            if err.errno == 1062:
                return False, "Username atau Email sudah terdaftar!"
            return False, str(err)
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def login_user(self, identity, password):
        if not self.is_connected: return None, "Database Terputus"
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            with self.lock:
                query = "SELECT * FROM users WHERE (username = %s OR email = %s) AND password = %s"
                cursor.execute(query, (identity, identity, password))
                user = cursor.fetchone()
            if user:
                return user, "Login Sukses"
            return None, "Username/Email atau Password salah!"
        except Exception as e:
            return None, str(e)
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def add_app_log(self, user_id, name, start, duration):
        if not self.is_connected or user_id is None: return
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            with self.lock:
                cursor.execute("INSERT INTO screentime (user_id, app_name, start_time, duration) VALUES (%s, %s, %s, %s)", 
                               (user_id, name, start, duration))
                conn.commit()
        except Exception as e:
            logger.error(" Error adding app log: %s", str(e))
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_aggregated_screentime(self, user_id, minutes=15):
        if not self.is_connected or user_id is None: return 0, 0
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT SUM(duration), COUNT(id) FROM screentime 
                WHERE user_id = %s AND start_time >= NOW() - INTERVAL %s MINUTE
            """
            cursor.execute(query, (user_id, minutes))
            result = cursor.fetchone()
            return (result[0] if result[0] else 0, result[1] if result[1] else 0)
        except Exception as e:
            logger.error(" Error aggregating screentime: %s", str(e))
            return 0, 0
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_all_app_logs(self, user_id):
        if not self.is_connected or user_id is None: return []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT app_name, start_time, duration FROM screentime WHERE user_id = %s ORDER BY start_time DESC LIMIT 50"
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(" Error getting app logs: %s", str(e))
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # Tambahkan metode ini di dalam class DBManager di database.py
    def get_performance_health_report(self, user_id):
        logger.info(f"[TRACE] Database Access: Fetching join data from health_metrics_logs & performa_logs for UserID: {user_id}")
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            # Melakukan JOIN antara kesehatan dan performa
            query = """
                SELECT 
                    h.timestamp, h.hr, h.rmssd, 
                    p.level_name, p.start_time, p.end_time 
                FROM health_metrics_logs h
                JOIN performa_logs p ON h.user_id = p.user_id
                WHERE h.user_id = %s 
                AND h.timestamp BETWEEN p.start_time AND p.end_time
                ORDER BY h.timestamp DESC
            """
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            logger.info(f"[TRACE] Database Access Success: Retrieved {len(results)} rows.")
            return results
        except Exception as e:
            logger.error(f"[TRACE] Database Access Failed: {e}")
            return []
        finally:
            if conn: conn.close()

    def insert_window_log(self, user_id, avg_hr, avg_rmssd):
        query = "INSERT INTO window_slicing_logs (user_id, start_time, end_time, avg_delta_hr, avg_delta_rmssd) VALUES (%s, NOW(), NOW(), %s, %s)"
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (user_id, avg_hr, avg_rmssd))
            window_id = cursor.lastrowid # Ambil ID terakhir untuk link ke prediction_logs
            conn.commit()
            cursor.close()
            conn.close()
            return window_id

    def insert_prediction_log(self, window_id, status, trend_score):
        query = "INSERT INTO prediction_logs (window_id, prediction_status, trend_score) VALUES (%s, %s, %s)"
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (window_id, status, trend_score))
            conn.commit()
            cursor.close()
            conn.close()