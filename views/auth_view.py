import flet as ft

class AuthView(ft.Container):
    def __init__(self, db, on_auth_success):
        super().__init__(
            # Hapus alignment='center' di sini, kita pindahkan ke page-level agar lebih aman
            expand=True,
            bgcolor="#0F1115" # Warna latar belakang page agar tidak hitam
        )
        self.db = db
        self.on_auth_success = on_auth_success
        
        input_style = {
            "bgcolor": "#111827",
            "color": "white",
            "border_color": "#2A2F3A",
            "focused_border_color": "#3B82F6",
        }

        # Bungkus form dalam container dengan ukuran pasti
        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("LOGIN", size=40, weight="bold", color="black"),
                    ft.TextField(label="Username", color="black"),
                    ft.TextField(label="Password", password=True, color="black"),
                    ft.ElevatedButton("Masuk", on_click=lambda e: print("Klik")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=ft.Colors.GREY_200, # Warna form agar terlihat jelas
            padding=20,
            border_radius=10,
            alignment="center"
        )

        # Inisialisasi textfield input secara aman
        self.identity_input = ft.TextField(
            label="Username atau Email",
            prefix_icon=ft.Icons.PERSON,
            **input_style
        )

        self.password_input = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
            **input_style
        )
        self.error_text = ft.Text(color="red", weight="bold")

        self.reg_user = ft.TextField(label="Username", prefix_icon=ft.Icons.PERSON, bgcolor="white", color="black")
        self.reg_email = ft.TextField(label="Email", prefix_icon=ft.Icons.EMAIL, bgcolor="white", color="black")
        self.reg_pass = ft.TextField(label="Password", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, bgcolor="white", color="black")
        self.reg_age = ft.TextField(label="Umur", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="white", color="black")
        self.reg_tb = ft.TextField(label="Tinggi Badan (cm)", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="white", color="black")
        self.reg_bb = ft.TextField(label="Berat Badan (kg)", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="white", color="black")
        
        self.reg_gender = ft.Dropdown(
            label="Jenis Kelamin",
            bgcolor="white",
            color="black",
            options=[
                ft.dropdown.Option("1", "Laki-laki"),
                ft.dropdown.Option("2", "Perempuan")
            ]
        )
        self.reg_error = ft.Text(color="red", weight="bold")

        # Set tampilan default awal secara langsung tanpa memicu self.update() prematur
        self.setup_login_content()

    def did_mount(self):
            # Dipanggil otomatis oleh Flet saat komponen sudah siap di layar
            print("🏗️ [AUTH VIEW] Komponen terpasang (did_mount), merender login...")
            self.show_login_page()

    def setup_login_content(self):
        self.content = ft.Card(
            elevation=10,
            bgcolor="#161A22",
            content=ft.Container(
                padding=40,
                expand=True,
                content=ft.Column(
                    [
                        ft.Text(
                            "SYSTEM EDGE AI",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color="white",
                        ),

                        # ft.Text(
                        #     "Sign in to continue",
                        #     color="#9CA3AF",
                        #     size=14,
                        # ),

                        ft.Divider(color="#2A2F3A"),

                        self.identity_input,
                        self.password_input,
                        self.error_text,

                        ft.Container(height=10),

                        ft.FilledButton(
                            "LOGIN",
                            icon=ft.Icons.LOGIN,
                            on_click=self.handle_login,
                            style=ft.ButtonStyle(
                                bgcolor="#3B82F6",
                                color="white",
                            ),
                            height=45,
                        ),

                        ft.TextButton(
                            "Buat akun baru",
                            on_click=lambda e: self.show_register_page(),
                            style=ft.ButtonStyle(color="#60A5FA"),
                        ),
                    ],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    def show_login_page(self):
        self.setup_login_content()
        try: self.update()
        except: pass

    def show_register_page(self):
        self.content = ft.Card(
            elevation=10,
            bgcolor="#161A22",
            content=ft.Container(
                padding=40,
                expand=True,
                content=ft.Column(
                    [
                        ft.Text(
                            "CREATE ACCOUNT",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="white",
                        ),

                        ft.Text(
                            "Fill in your data",
                            color="#9CA3AF",
                        ),

                        ft.Divider(color="#2A2F3A"),

                        self.reg_user,
                        self.reg_email,
                        self.reg_pass,

                        ft.Row(
                            [self.reg_age, self.reg_gender],
                            spacing=10,
                        ),

                        ft.Row(
                            [self.reg_tb, self.reg_bb],
                            spacing=10,
                        ),

                        self.reg_error,

                        ft.Container(height=10),

                        ft.FilledButton(
                            "Daftar",
                            icon=ft.Icons.HOW_TO_REG,
                            on_click=self.handle_register,
                            style=ft.ButtonStyle(
                                bgcolor="#22C55E",
                                color="white",
                            ),
                            height=45,
                        ),

                        ft.TextButton(
                            "Kembali ke login",
                            on_click=lambda e: self.show_login_page(),
                            style=ft.ButtonStyle(color="#60A5FA"),
                        ),
                    ],
                    spacing=12,
                ),
            ),
        )

        try:
            self.update()
        except:
            pass

    def handle_login(self, e):
        identity = self.identity_input.value.strip()
        password = self.password_input.value.strip()

        if not identity or not password:
            self.error_text.value = "Semua field wajib diisi!"
            self.update()
            return

        user, msg = self.db.login_user(identity, password)
        if user:
            self.on_auth_success(user)
        else:
            self.error_text.value = msg
            self.update()

    def handle_register(self, e):
        u = self.reg_user.value.strip()
        em = self.reg_email.value.strip()
        p = self.reg_pass.value.strip()
        age = self.reg_age.value.strip()
        g_id = self.reg_gender.value
        tb = self.reg_tb.value.strip()
        bb = self.reg_bb.value.strip()

        if not all([u, em, p, age, g_id, tb, bb]):
            self.reg_error.value = "Semua field wajib diisi!"
            self.update()
            return

        success, msg = self.db.register_user(u, em, p, int(age), int(g_id), float(tb), float(bb))
        if success:
            self.show_login_page()
            self.identity_input.value = u
            self.error_text.value = "Registrasi sukses! Silakan login."
            self.error_text.color = "green"
            self.update()
        else:
            self.reg_error.value = msg
            self.update()