import flet as ft

class DashboardView(ft.Column):
    def __init__(self, ai_status, start_conn_callback):
<<<<<<< HEAD
        super().__init__(spacing=10, expand=True)
=======
        super().__init__(spacing=15, scroll="auto")
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
        self.ai_status = ai_status
        self.start_conn_callback = start_conn_callback
        
        # 1. INISIALISASI REFERENSI
        self.hr_ref = ft.Ref[ft.Text]()
        self.status_ref = ft.Ref[ft.Text]()
<<<<<<< HEAD
        self.log_ref = ft.Ref[ft.ListView]()
        self.profile_info_text = ft.Text("Memuat data profil...", size=12, italic=True)
        self.kebisingan_ref = ft.Ref[ft.Text]()
        self.rekomendasi1_ref = ft.Ref[ft.Text]()
        self.rekomendasi2_ref = ft.Ref[ft.Text]()
        self.kipas_ref = ft.Ref[ft.Text]()
        self.lampu_ref = ft.Ref[ft.Text]()
=======
        self.web_level_ref = ft.Ref[ft.Text]()
        self.web_timer_ref = ft.Ref[ft.Text]()
        self.log_ref = ft.Ref[ft.ListView]()
        self.profile_info_text = ft.Text("Memuat data profil...", size=13, italic=True)
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3

        # 2. BUAT KOMPONEN
        self._build_components()

        # 3. SUSUN LAYOUT
        self.controls = self._build_layout()

    def _build_components(self):
        # Panel Kalibrasi
<<<<<<< HEAD
        self.calib_countdown_text = ft.Text("03:00", size=28, weight="bold", color="blue")
        self.calib_progress_bar = ft.ProgressBar(value=0.0, width=300, color="blue")
=======
        self.calib_countdown_text = ft.Text("03:00", size=36, weight="bold", color="blue")
        self.calib_progress_bar = ft.ProgressBar(value=0.0, width=400, color="blue")
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
        
        self.calibration_panel = ft.Container(
            content=ft.Column([
                ft.Row([
<<<<<<< HEAD
                    ft.Icon(ft.Icons.ACCESSIBILITY_NEW, color="blue", size=18), 
                    ft.Text("PROSES KALIBRASI AWAL", size=14, weight="bold", color="blue")
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text("Mohon duduk tegak, rileks, dan jaga posisi.", size=11, color="blue"),
                ft.Row([self.calib_countdown_text], alignment=ft.MainAxisAlignment.CENTER),
                self.calib_progress_bar,
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=10, bgcolor="#1A1F2C", border_radius=8, visible=True
        )

        # Status Card
        self.status_card = ft.Container(
            content=ft.Column([
                ft.Text("Status Kelelahan", size=12, color=ft.Colors.GREY_400),
                ft.Text(ref=self.status_ref, value="NORMAL", size=20, weight="bold", color="green"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10, 
            border_radius=10, 
            bgcolor="#1A1F2C",
            expand=True
        )
        
        # HR Card
        self.hr_card = ft.Container(
            content=ft.Column([
                ft.Text("Detak Jantung", size=12, color=ft.Colors.GREY_400),
                ft.Text("0 BPM", size=20, weight="bold", ref=self.hr_ref, color="blue"),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10, 
            border_radius=10, 
            bgcolor="#1A1F2C",
            expand=True
        )

        # Card Custom Box
        self.environment_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SETTINGS_REMOTE, color="orange", size=16),
                        ft.Text("Status Custom Box", weight="bold", size=13)
                    ], tight=True),
                    ft.Row([
                        ft.Text("Kebisingan:", size=11, color=ft.Colors.GREY_400),
                        ft.Text(ref=self.kebisingan_ref, value="-- dB", size=11, weight="bold"),
                        ft.VerticalDivider(),
                        ft.Text("Kipas:", size=11, color=ft.Colors.GREY_400),
                        ft.Text(ref=self.kipas_ref, value="Level -", size=11, weight="bold"),
                        ft.VerticalDivider(),
                        ft.Text("Lampu:", size=11, color=ft.Colors.GREY_400),
                        ft.Text(ref=self.lampu_ref, value="Level -", size=11, weight="bold"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color="orange"),
                            ft.Text(ref=self.rekomendasi1_ref, value="-", size=11)], tight=True),
                ], spacing=4),
                padding=10
            )
=======
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
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
        )

    def _build_layout(self):
        return [
<<<<<<< HEAD
            ft.Row([
                ft.Text("Dashboard Utama", size=20, weight="bold"),
                ft.Text(f"AI: {self.ai_status}", size=11, color="green" if "Active" in self.ai_status else "red")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=2),
            ft.Row([self.status_card, self.hr_card], spacing=10),
            self.calibration_panel,
            ft.Card(content=ft.Container(content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color="blue", size=16), ft.Text("Profil Operator", weight="bold", size=12)]), 
                self.profile_info_text
            ], spacing=2), padding=10)),
            self.environment_card,
            ft.Card(content=ft.Container(content=ft.Column([
                ft.Text("Log Sistem", weight="bold", size=12), 
                ft.ListView(ref=self.log_ref, height=80, spacing=2, expand=True)
            ], spacing=2), padding=10), expand=True)
=======
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
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
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
<<<<<<< HEAD
            print(f"UI Error: {e}")

    def update_environment_ui(self, kebisingan, kipas_pwm, lampu_persen):
        try:
            self.kebisingan_ref.current.value = f"{kebisingan}" if kebisingan is not None else "-- "
            kipas_map = {125: 1, 140: 2, 170: 3, 200: 4, 230: 5, 255: 6}
            self.kipas_ref.current.value = f"Lvl {kipas_map.get(kipas_pwm, '-')}"
            lampu_map = {0: 1, 20: 2, 50: 3, 75: 4, 100: 5}
            self.lampu_ref.current.value = f"Lvl {lampu_map.get(lampu_persen, '-')}"
            
            if kebisingan is not None and kebisingan > 15000:
                self.rekomendasi1_ref.current.value = "Lingkungan cukup bising."
            else:
                self.rekomendasi1_ref.current.value = "Kondisi lingkungan ideal."
            self.update()
        except Exception as e:
            print(f"UI Error (environment): {e}")
=======
            print(f"UI Error: {e}")
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
