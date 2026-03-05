"""
ui/profile_page.py - Shows user info and QR print button (page-profile).
"""

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD
import hardware_hooks


class ProfilePage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "My Profile").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        card = ctk.CTkFrame(
            self,
            fg_color=C["white"],
            corner_radius=14,
            border_color=C["aqua"],
            border_width=2,
        )
        card.grid(row=1, column=0, padx=PAD, pady=8, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=0)

        # ── Left: user text ───────────────────────────────────────────────────
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, padx=PAD, pady=PAD, sticky="nw")

        self._lbl_user  = self.make_label(info, "Username: —", font=F["sub"])
        self._lbl_phone = self.make_label(info, "Phone: —")
        self._lbl_email = self.make_label(info, "Email: —")
        self._lbl_pts   = self.make_label(info, "Points: 0", font=F["sub"])

        for idx, lbl in enumerate(
            [self._lbl_user, self._lbl_phone, self._lbl_email, self._lbl_pts]
        ):
            lbl.grid(row=idx, column=0, pady=4, sticky="w")

        self.make_button(
            info, "🖨  Print QR",
            command=self._print_qr,
            color=C["dark_blue"],
            height=44,
            font=F["btn"],
        ).grid(row=4, column=0, pady=(14, 0), sticky="ew")

        # ── Right: QR placeholder ─────────────────────────────────────────────
        qr_frame = ctk.CTkFrame(
            card,
            width=100, height=100,
            fg_color=C["white"],
            border_color="#333333",
            border_width=2,
            corner_radius=4,
        )
        qr_frame.grid(row=0, column=1, padx=PAD, pady=PAD, sticky="ne")
        qr_frame.grid_propagate(False)

        ctk.CTkLabel(
            qr_frame,
            text="QR",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color="#333333",
        ).place(relx=0.5, rely=0.5, anchor="center")

        self.make_back_button(self, "dashboard").grid(
            row=2, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def on_show(self) -> None:
        u = self.app_state.user
        self._lbl_user.configure(text=f"Username:  {u.username}")
        self._lbl_phone.configure(text=f"Phone:     {u.phone}")
        self._lbl_email.configure(text=f"Email:     {u.email}")
        self._lbl_pts.configure(text=f"Points:    {u.points}")

    def _print_qr(self) -> None:
        hardware_hooks.print_qr(
            self.app_state.user.username,
            self.controller.serial_mgr,
        )
        self.controller.show_alert("QR Printed", "Your QR receipt is printing…")
