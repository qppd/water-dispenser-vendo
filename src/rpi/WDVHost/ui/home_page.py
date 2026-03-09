import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, BTN_WIDE, PAD


class HomePage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(list(range(10)), weight=0)
        center.rowconfigure(2, weight=1)   # spacer grows

        # ── Title ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            center,
            text="💧 AQUA SPLASH",
            font=ctk.CTkFont("Segoe UI", 38, "bold"),
            text_color=C["dark_blue"],
        ).grid(row=0, column=0, pady=(60, 4))

        ctk.CTkLabel(
            center,
            text="Purified Water Dispenser",
            font=ctk.CTkFont(*F["sub"]),
            text_color=C["steel"],
        ).grid(row=1, column=0, pady=(0, 30))

        # ── Button row 1 ──────────────────────────────────────────────────────
        row1 = ctk.CTkFrame(center, fg_color="transparent")
        row1.grid(row=3, column=0, pady=6)

        self.make_button(
            row1, "🔲  QR Login",
            command=self._qr_login,
            color=C["dark_blue"],
            width=BTN_WIDE,
            height=BTN_HEIGHT,
        ).pack(side="left", padx=8)

        self.make_button(
            row1, "🔐  Sign In",
            command=lambda: self.controller.show_page("signin"),
            color=C["btn_other"],
            width=BTN_WIDE,
            height=BTN_HEIGHT,
        ).pack(side="left", padx=8)

        # ── Button row 2 ──────────────────────────────────────────────────────
        self.make_button(
            center, "✅  Activate Account",
            command=lambda: self.controller.show_page("register"),
            color=C["accent"],
            width=BTN_WIDE * 2 + 16,
            height=BTN_HEIGHT,
        ).grid(row=4, column=0, pady=6)

        self.make_button(
            center, "👤  Continue as Guest",
            command=self._guest_login,
            color=C["steel"],
            width=BTN_WIDE * 2 + 16,
            height=BTN_HEIGHT,
        ).grid(row=5, column=0, pady=6)

        # spacer at bottom
        ctk.CTkFrame(center, fg_color="transparent", height=40).grid(row=6, column=0)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _guest_login(self) -> None:
        self.app_state.login_guest()
        self.controller.show_page("dashboard")
        self.controller.sidebar.refresh()

    def _qr_login(self) -> None:
        self.controller.show_page("qr_scan")
