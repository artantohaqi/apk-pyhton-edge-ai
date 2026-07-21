import flet as ft
from datetime import datetime

class ScreentimeView(ft.Column):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db
<<<<<<< HEAD
        self.saved_user_id = None
        
        self.user_dropdown = ft.Dropdown(
            label="Pilih User",
            width=200,
            bgcolor=ft.Colors.GREY_800,
            color=ft.Colors.WHITE
        )
        self.user_dropdown.on_change = self.on_user_select
        
        self.table_container = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS)
        
        self.controls = [
            ft.Row([
                ft.Column([
                    ft.Text("Riwayat Prediksi Sliding Window (AI)", size=22, weight="bold", color=ft.Colors.BLUE_400),
                    ft.Text("Menampilkan hasil inferensi model dari tabel prediction_logs", size=11, color=ft.Colors.GREY_400),
                ]),
                ft.Row([
                    self.user_dropdown,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, 
                        icon_color=ft.Colors.BLUE_400,
                        on_click=self.refresh_data, 
                        tooltip="Refresh Data"
                    )
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            self.table_container
        ]
        self.load_users()

    def load_users(self):
        try:
            users = self.db.get_all_users()
            options = [ft.dropdown.Option(str(u['id']), f"{u['username']} (ID: {u['id']})") for u in users]
            self.user_dropdown.options = options
            if options:
                self.user_dropdown.value = options[0].key
                self.saved_user_id = int(options[0].key)
                self.refresh_data(None, self.saved_user_id)
        except Exception as ex:
            print(f"Error load users: {ex}")

    def on_user_select(self, e):
        if self.user_dropdown.value:
            self.saved_user_id = int(self.user_dropdown.value)
            self.refresh_data(None, self.saved_user_id)

    def refresh_data(self, e=None, user_id=None):
        if user_id is None:
            user_id = self.saved_user_id
        
        self.table_container.controls.clear()

        if user_id is None:
            self.table_container.controls.append(ft.Text("User tidak teridentifikasi.", color="red"))
=======
        
        # Initial controls
        self.controls = [
            ft.Row([
                ft.Column([
                    ft.Text("Riwayat Aktivitas Laptop", size=25, weight="bold"),
                    ft.Text("Mencatat durasi aplikasi foreground window", size=12, color="grey"),
                ]),
                ft.IconButton(
                    icon=ft.Icons.REFRESH, 
                    on_click=self.refresh_data, 
                    tooltip="Refresh Data"
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Text("Loading...", color="grey")
        ]

    def refresh_data(self, e=None, user_id=None):
        print("📊 ScreentimeView: Refreshing data...")
        self.controls.clear()
        
        self.controls.append(
            ft.Row([
                ft.Column([
                    ft.Text("Riwayat Aktivitas Laptop", size=25, weight="bold"),
                    ft.Text("Mencatat durasi aplikasi foreground window", size=12, color="grey"),
                ]),
                ft.IconButton(
                    icon=ft.Icons.REFRESH, 
                    on_click=lambda _: self.refresh_data(None, user_id),
                    tooltip="Refresh Data"
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        self.controls.append(ft.Divider())

        if user_id is None:
            self.controls.append(ft.Text("User tidak teridentifikasi.", color="red"))
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
            try: self.update()
            except: pass
            return

<<<<<<< HEAD
        logs = self.db.get_prediction_logs(user_id)
        rows = []
        for log in logs:
            time_display = log.get('timestamp')
=======
        # Ambil data spesifik berdasarkan user_id aktif
        logs = self.db.get_all_app_logs(user_id)
        rows = []
        for log in logs:
            time_display = log['start_time']
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
            if isinstance(time_display, datetime):
                time_display = time_display.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_display = str(time_display)

<<<<<<< HEAD
            status_ai = log.get('prediction_status', 'NORMAL')
            trend_score = log.get('trend_score', 0.0)
            status_color = ft.Colors.RED_400 if status_ai == "DIGITAL FATIGUE" else ft.Colors.GREEN_400

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(log.get('window_id', '-')), size=12, weight="bold")),
                    ft.DataCell(ft.Text(time_display, size=12)),
                    ft.DataCell(ft.Text(status_ai, size=12, weight="bold", color=status_color)),
                    ft.DataCell(ft.Text(str(trend_score), size=12)),
=======
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(log['app_name'] if log['app_name'] else "Unknown", size=12, weight="bold")),
                    ft.DataCell(ft.Text(time_display, size=12)),
                    ft.DataCell(ft.Text(f"{log['duration']} detik", size=12, color="blue")),
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
                ])
            )

        if not rows:
<<<<<<< HEAD
            self.table_container.controls.append(
                ft.Container(
                    content=ft.Text("Belum ada riwayat prediksi AI untuk user ini.", color="grey", italic=True),
                    padding=20,
                    alignment="center"  # Diperbaiki dari ft.alignment.center menjadi string "center"
                )
            )
        else:
            self.table_container.controls.append(
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Window ID", weight="bold")),
                        ft.DataColumn(ft.Text("Waktu Prediksi", weight="bold")),
                        ft.DataColumn(ft.Text("Status AI", weight="bold")),
                        ft.DataColumn(ft.Text("Trend Score", weight="bold")),
                    ],
                    rows=rows,
                    heading_row_color=ft.Colors.GREY_800,
=======
            self.controls.append(
                ft.Container(
                    content=ft.Text("Belum ada riwayat aplikasi yang tercatat untuk user ini.", color="grey", italic=True),
                    padding=20,
                    alignment="center"
                )
            )
        else:
            self.controls.append(
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Nama Aplikasi", weight="bold")),
                        ft.DataColumn(ft.Text("Waktu Mulai", weight="bold")),
                        ft.DataColumn(ft.Text("Durasi Aktif", weight="bold")),
                    ],
                    rows=rows,
                    heading_row_color=ft.Colors.BLACK12,
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
                    divider_thickness=1,
                )
            )
        try: self.update()
        except: pass