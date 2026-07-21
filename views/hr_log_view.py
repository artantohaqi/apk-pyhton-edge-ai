import flet as ft
from datetime import datetime

class HRLogView(ft.Column):
    def __init__(self, db):
        super().__init__(expand=True, scroll=ft.ScrollMode.ALWAYS)
        self.db = db
        self.saved_user_id = None 
        
<<<<<<< HEAD
        self.user_dropdown = ft.Dropdown(
            label="Pilih User",
            width=200,
            bgcolor=ft.Colors.GREY_800,
            color=ft.Colors.WHITE
        )
        self.user_dropdown.on_change = self.on_user_select
        
=======
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
        self.table_container = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS)
        
        self.controls = [
            ft.Row([
                ft.Column([
<<<<<<< HEAD
                    ft.Text("Log Sliding Window & Fisiologis", size=22, weight="bold", color=ft.Colors.BLUE_400),
                    ft.Text("Menampilkan hasil ekstraksi per window dari tabel window_slicing_logs", size=11, color=ft.Colors.GREY_400),
                ]),
                ft.Row([
                    self.user_dropdown,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, 
                        icon_color=ft.Colors.BLUE_400,
                        on_click=self.refresh_data, 
                        tooltip="Refresh Tabel Data"
                    )
                ])
=======
                    ft.Text("Log Ekstraksi Parameter Delta & Klasifikasi AI", size=22, weight="bold", color=ft.Colors.BLUE_400),
                    ft.Text("Menampilkan tabel runtun waktu parameter penyusutan variabilitas (Delta RMSSD) dan lonjakan detak jantung (Delta HR)", size=11, color=ft.Colors.GREY_400),
                ]),
                ft.IconButton(
                    icon=ft.Icons.REFRESH, 
                    icon_color=ft.Colors.BLUE_400,
                    on_click=self.refresh_data, 
                    tooltip="Refresh Tabel Data"
                )
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_700),
            self.table_container
        ]
<<<<<<< HEAD
        self.load_users()

    def load_users(self):
        try:
            users = self.db.get_all_users()
            options = [ft.dropdown.Option(str(u['id']), f"{u['username']} (ID: {u['id']})") for u in users]
            self.user_dropdown.options = options
            if options:
                self.user_dropdown.value = options[0].key
                self.saved_user_id = int(options[0].key)
        except Exception as ex:
            print(f"Error load users: {ex}")

    def on_user_select(self, e):
        if self.user_dropdown.value:
            self.update_logs(int(self.user_dropdown.value))
=======
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3

    def update_logs(self, user_id):
        self.saved_user_id = user_id
        self.table_container.controls.clear()
        
        if not self.db.is_connected:
            self.table_container.controls.append(ft.Text("✗ Database tidak terhubung.", color="red"))
<<<<<<< HEAD
            try:
                self.update()
            except Exception:
                pass
            return

        logs = self.db.get_window_slicing_logs(user_id)
        if not logs:
            self.table_container.controls.append(
                ft.Container(
                    content=ft.Text("Belum ada data window slicing untuk user ini.", color=ft.Colors.GREY_500, size=13),
                    padding=20
                )
            )
            try:
                self.update()
            except Exception:
                pass
=======
            self.page.update()
            return

        # Ambil data metriks dari fungsi database
        logs = self.db.get_health_logs(user_id)
        if not logs:
            self.table_container.controls.append(
                ft.Container(
                    content=ft.Text("Belum ada data rekam monitoring fisiologis untuk user ini.", color=ft.Colors.GREY_500, size=13),
                    padding=20
                )
            )
            self.page.update()
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
            return

        table_rows = []
        for log in logs:
<<<<<<< HEAD
            d_hr = log.get('avg_delta_hr', 0.0)
            d_rmssd = log.get('avg_delta_rmssd', 0.0)
            dt_obj = log.get('start_time')
            time_str = dt_obj.strftime("%H:%M:%S") if isinstance(dt_obj, datetime) else str(dt_obj)

            table_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(log.get('id', '-')), size=12, color=ft.Colors.WHITE)),
                        ft.DataCell(ft.Text(time_str, size=12, color=ft.Colors.GREY_300)),
                        ft.DataCell(ft.Text(f"{d_hr:.2f}", size=12, color=ft.Colors.WHITE)),
                        ft.DataCell(ft.Text(f"{d_rmssd:.2f}", size=12, color=ft.Colors.WHITE)),
=======
            # Ambil nilai delta dari record database (sediakan fallback jika null)
            d_hr = log.get('delta_hr') if log.get('delta_hr') is not None else 0.0
            d_rmssd = log.get('delta_rmssd') if log.get('delta_rmssd') is not None else 0.0
            status_str = log.get('status_ai', 'NORMAL')
            
            # Formatisasi teks penanda visual waktu kaku
            dt_obj = log.get('recorded_at')
            time_str = dt_obj.strftime("%H:%M:%S") if isinstance(dt_obj, datetime) else str(dt_obj)

            # Pewarnaan dinamis baris status keputusan XGBoost
            if status_str == "DIGITAL FATIGUE":
                status_color = ft.Colors.RED_400
            elif status_str == "STRESS":
                status_color = ft.Colors.ORANGE_400
            else:
                status_color = ft.Colors.GREEN_400

            table_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(time_str, size=12, color=ft.Colors.GREY_300)),
                        ft.DataCell(ft.Text(f"+{d_hr:.1f} BPM" if d_hr > 0 else f"{d_hr:.1f} BPM", size=12, color=ft.Colors.WHITE)),
                        ft.DataCell(ft.Text(f"{d_rmssd:.1f} %", size=12, color=ft.Colors.WHITE)),
                        ft.DataCell(ft.Text(status_str, size=12, weight="bold", color=status_color)),
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
                    ]
                )
            )

        self.table_container.controls.append(
            ft.Row([
                ft.DataTable(
                    columns=[
<<<<<<< HEAD
                        ft.DataColumn(ft.Text("Window ID", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Waktu Mulai", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Rata-rata Delta HR", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Rata-rata Delta RMSSD", weight="bold", color=ft.Colors.BLUE_300)),
=======
                        ft.DataColumn(ft.Text("Waktu", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Delta HR (Lonjakan)", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Delta RMSSD (Penyusutan)", weight="bold", color=ft.Colors.BLUE_300)),
                        ft.DataColumn(ft.Text("Status AI (XGBoost)", weight="bold", color=ft.Colors.BLUE_300)),
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3
                    ],
                    rows=table_rows,
                    heading_row_color=ft.Colors.GREY_800,
                    divider_thickness=1,
                    horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_700),
                )
            ], scroll=ft.ScrollMode.ALWAYS)
        )
        try:
<<<<<<< HEAD
            self.update()
        except Exception:
            pass
=======
            self.page.update()
        except: pass
>>>>>>> 98367951641cbdfd2bce23d201baa6fa15f166a3

    def refresh_data(self, e):
        if self.saved_user_id:
            self.update_logs(self.saved_user_id)