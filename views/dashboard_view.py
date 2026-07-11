import flet as ft

class DashboardView(ft.Column):
    def __init__(self, ai_status, start_conn_callback):
        super().__init__(spacing=15, scroll="auto")
        self.ai_status = ai_status
        self.start_conn_callback = start_conn_callback
        
        # --- KOMPONEN PANEL INTEGRASI KALIBRASI INTERNAL ---
        self.calib_countdown_text = ft.Text("03:00", size=36, weight="bold", color="blue")
        self.calib_progress_bar = ft.ProgressBar(value=0.0, width=400, color="blue")
        
        self.calib_tutorial_text = ft.Text(
            "Mohon duduk tegak, rileks, dan jaga posisi.\n"
            "Jangan berbicara atau melakukan gerakan mendadak selama 3 menit.\n"
            "Ketenangan Anda sangat krusial untuk akurasi deteksi fatigue.",
            size=13, 
            text_align="center", 
            color="blue" # Ubah warna agar lebih mencolok perhatian
        )
        
        self.calibration_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ACCESSIBILITY_NEW, color="blue"),
                    ft.Text("PROSES KALIBRASI AWAL", size=16, weight="bold", color="blue")
                ], alignment=ft.MainAxisAlignment.CENTER),
                self.calib_tutorial_text,
                ft.Row([self.calib_countdown_text], alignment=ft.MainAxisAlignment.CENTER),
                self.calib_progress_bar,
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=20,
            bgcolor="#1A1F2C",
            border_radius=10,
            visible=True  
        )

        self.setup_ui()

    def setup_ui(self):
        self.web_level_ref = ft.Ref[ft.Text]()
        self.web_timer_ref = ft.Ref[ft.Text]()
        self.hr_ref = ft.Ref[ft.Text]()
        self.status_ref = ft.Ref[ft.Text]()
        self.log_ref = ft.Ref[ft.ListView]()
        self.profile_info_text = ft.Text("Memuat data profil...", size=13, italic=True)

        self.controls = [
            ft.Row([
                ft.Column([
                    ft.Text("Dashboard Utama", size=28, weight="bold"),
                    ft.Text(f"Status Model AI: {self.ai_status}", size=12, color="green" if "Active" in self.ai_status else "red"),
                ]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),

            self.calibration_panel,

            # Card Profil Operator Pengguna
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color="blue"), ft.Text("Profil Operator Sistem", weight="bold")]),
                        self.profile_info_text
                    ]), padding=15
                )
            ),

            # Row Data Gelang Real-Time
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([ft.Text("Detak Jantung Aktual"), ft.Text("0 BPM", size=30, weight="bold", ref=self.hr_ref)]), 
                        padding=20
                    ), expand=1
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([ft.Text("Kondisi Saat Ini"), ft.Text("CALIBRATING", size=20, weight="bold", color="blue", ref=self.status_ref)]), 
                        padding=25
                    ), expand=1
                ),
            ]),

            # Card Stopwatch Lini Masa Web Tes
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Lini Masa Eksperimen Aplikasi Web Buatan Sendiri", weight="bold"),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.WEB, color="blue", size=40),
                            title=ft.Text("Menunggu aktivitas pengerjaan level...", ref=self.web_level_ref, weight="bold"),
                            subtitle=ft.Text("Stopwatch Waktu: 0s", ref=self.web_timer_ref)
                        )
                    ]), padding=20
                )
            ),
            
            # Log Stream Sinyal Gelang
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Aliran Sinyal Gelang & Log Sistem", weight="bold"),
                        ft.Divider(color="grey", height=5),
                        ft.ListView(ref=self.log_ref, height=120, spacing=5, scroll="always")
                    ]), padding=15
                )
            )
        ]

    def update_profile_ui(self, user_data):
        gender_str = "Laki-laki" if user_data['kelamin_id'] == 1 else "Perempuan"
        self.profile_info_text.value = (
            f"User: {user_data['username']} ({user_data['email']})  |  "
            f"Fisik: {user_data['age']} Thn, {user_data['tb']} cm, {user_data['bb']} kg ({gender_str})"
        )
        try: self.update()
        except: pass

    def update_calibration_ui(self, remaining_seconds, total_seconds=300):
        try:
            # 1. Hitung format menit dan detik kaku
            mins = remaining_seconds // 60
            secs = remaining_seconds % 60
            
            # 2. Update nilai teks visual hitung mundur
            self.calib_countdown_text.value = f"{mins:02d}:{secs:02d}"
            
            # 3. Hitung rasio perkembangan progress bar (0.0 sampai 1.0)
            elapsed_seconds = total_seconds - remaining_seconds
            progress_ratio = elapsed_seconds / total_seconds
            self.calib_progress_bar.value = min(max(progress_ratio, 0.0), 1.0)
            
            # 4. CRITICAL FIX: Paksa Flet untuk me-refresh visual komponen di layar detik itu juga
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception as e:
            print(f"⚠️ [UI WARNING] Gagal update visual kalibrasi: {e}")