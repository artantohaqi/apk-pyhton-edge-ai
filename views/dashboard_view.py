import flet as ft

class DashboardView(ft.Column):
    def __init__(self, ai_status, start_conn_callback):
        super().__init__(spacing=15, scroll="auto")
        self.ai_status = ai_status
        self.start_conn_callback = start_conn_callback
        
        # 1. INISIALISASI REFERENSI
        self.hr_ref = ft.Ref[ft.Text]()
        self.status_ref = ft.Ref[ft.Text]()
        self.web_level_ref = ft.Ref[ft.Text]()
        self.web_timer_ref = ft.Ref[ft.Text]()
        self.log_ref = ft.Ref[ft.ListView]()
        self.profile_info_text = ft.Text("Memuat data profil...", size=13, italic=True)

        # 2. BUAT KOMPONEN
        self._build_components()

        # 3. SUSUN LAYOUT
        self.controls = self._build_layout()

    def _build_components(self):
        # Panel Kalibrasi
        self.calib_countdown_text = ft.Text("03:00", size=36, weight="bold", color="blue")
        self.calib_progress_bar = ft.ProgressBar(value=0.0, width=400, color="blue")
        
        self.calibration_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ACCESSIBILITY_NEW, color="blue"), 
                    ft.Text("PROSES KALIBRASI AWAL", size=16, weight="bold", color="blue")
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text("Mohon duduk tegak, rileks, dan jaga posisi.\nKetenangan Anda sangat krusial.", 
                        size=13, text_align=ft.TextAlign.CENTER, color="blue"),
                ft.Row([self.calib_countdown_text], alignment=ft.MainAxisAlignment.CENTER),
                self.calib_progress_bar,
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=20, bgcolor="#1A1F2C", border_radius=10, visible=True
        )

        # Status Card (Gunakan alignment.center dari ft, bukan modul terpisah)
        self.status_card = ft.Container(
            content=ft.Column([
                ft.Text("Status Kelelahan", size=14, color=ft.Colors.GREY_400),
                ft.Text(ref=self.status_ref, value="NORMAL", size=24, weight="bold", color="green"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, 
            border_radius=15, 
            bgcolor="#1A1F2C", 
            # alignment=ft.alignment.center
        )

    def _build_layout(self):
        return [
            ft.Text("Dashboard Utama", size=28, weight="bold"),
            ft.Text(f"Status Model AI: {self.ai_status}", size=12, color="green" if "Active" in self.ai_status else "red"),
            ft.Divider(),
            self.status_card,
            self.calibration_panel,
            ft.Card(content=ft.Container(content=ft.Column([ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color="blue"), ft.Text("Profil Operator", weight="bold")]), self.profile_info_text]), padding=15)),
            ft.Row([
                ft.Card(content=ft.Container(content=ft.Column([ft.Text("Detak Jantung"), ft.Text("0 BPM", size=30, weight="bold", ref=self.hr_ref)]), padding=20), expand=1),
            ]),
            ft.Card(content=ft.Container(content=ft.Column([ft.Text("Log Sistem", weight="bold"), ft.ListView(ref=self.log_ref, height=120, spacing=5, scroll="always")]), padding=15))
        ]

    def update_profile_ui(self, user_data):
        gender_str = "Laki-laki" if user_data.get('kelamin_id') == 1 else "Perempuan"
        self.profile_info_text.value = f"User: {user_data.get('username')} | {user_data.get('age')} Thn, {user_data.get('tb')} cm, {user_data.get('bb')} kg ({gender_str})"
        self.update()

    def update_calibration_ui(self, remaining_seconds, total_seconds=300):
        try:
            mins, secs = divmod(remaining_seconds, 60)
            self.calib_countdown_text.value = f"{mins:02d}:{secs:02d}"
            progress_ratio = (total_seconds - remaining_seconds) / total_seconds
            self.calib_progress_bar.value = min(max(progress_ratio, 0.0), 1.0)
            self.update()
        except Exception as e:
            print(f"UI Error: {e}")