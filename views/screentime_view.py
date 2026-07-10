import flet as ft
from datetime import datetime

class ScreentimeView(ft.Column):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db
        
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
            try: self.update()
            except: pass
            return

        # Ambil data spesifik berdasarkan user_id aktif
        logs = self.db.get_all_app_logs(user_id)
        rows = []
        for log in logs:
            time_display = log['start_time']
            if isinstance(time_display, datetime):
                time_display = time_display.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_display = str(time_display)

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(log['app_name'] if log['app_name'] else "Unknown", size=12, weight="bold")),
                    ft.DataCell(ft.Text(time_display, size=12)),
                    ft.DataCell(ft.Text(f"{log['duration']} detik", size=12, color="blue")),
                ])
            )

        if not rows:
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
                    divider_thickness=1,
                )
            )
        try: self.update()
        except: pass