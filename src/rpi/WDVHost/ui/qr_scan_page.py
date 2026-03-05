"""
ui/qr_scan_page.py - QR scanner animation + login (page-qr-scan).

In real hardware, the ESP32-attached QR reader would emit a "QR:{username}"
serial event.  In simulation mode, the first stored account is loaded after
2 s — mirroring the HTML simulation behaviour.
"""

from __future__ import annotations
from typing import Optional

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, PAD
from app_state import User
import storage
import hardware_hooks


class QRScanPage(BasePage):

    def build(self) -> None:
        self.configure(fg_color="#000000")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(list(range(4)), weight=0)
        center.rowconfigure(4, weight=1)

        # ── Scanner box ───────────────────────────────────────────────────────
        scan_outer = ctk.CTkFrame(
            center,
            width=160, height=160,
            fg_color="#111111",
            border_color=C["aqua"],
            border_width=4,
            corner_radius=0,
        )
        scan_outer.grid(row=0, column=0, pady=(80, 10))
        scan_outer.grid_propagate(False)

        # Animated sweep bar
        self._bar = ctk.CTkFrame(
            scan_outer,
            height=4,
            fg_color=C["accent"],
        )
        self._bar.place(x=0, y=0, relwidth=1.0)

        ctk.CTkLabel(
            center,
            text="Scanning…",
            font=ctk.CTkFont(*F["heading"]),
            text_color=C["white"],
        ).grid(row=1, column=0, pady=10)

        ctk.CTkLabel(
            center,
            text="Present your QR card to the reader",
            font=ctk.CTkFont(*F["body"]),
            text_color="#b3e5fc",
        ).grid(row=2, column=0, pady=4)

        self.make_button(
            center, "← Cancel",
            command=lambda: self.controller.show_page("home"),
            color=C["btn_back"],
            height=40,
            font=F["small"],
        ).grid(row=3, column=0, pady=20)

        self._scan_box   = scan_outer
        self._bar_y      = 0
        self._bar_dir    = 1
        self._anim_job: Optional[str] = None
        self._scan_job:  Optional[str] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        hardware_hooks.scan_qr(self.controller.serial_mgr)
        self._bar_y   = 0
        self._bar_dir = 1
        self._animate_bar()

        # Simulate QR result after 2 s (matches HTML simulation)
        self._scan_job = self.after(2000, self._process_scan)

    def _stop(self) -> None:
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        if self._scan_job:
            self.after_cancel(self._scan_job)
            self._scan_job = None

    # ── Bar animation ─────────────────────────────────────────────────────────

    def _animate_bar(self) -> None:
        box_h = 152   # inner height of scan box (160 - 4 border*2 - bar height)
        self._bar_y += self._bar_dir * 3
        if self._bar_y >= box_h:
            self._bar_y = box_h
            self._bar_dir = -1
        elif self._bar_y <= 0:
            self._bar_y = 0
            self._bar_dir = 1
        self._bar.place(x=0, y=self._bar_y, relwidth=1.0)
        self._anim_job = self.after(16, self._animate_bar)  # ~60 fps

    # ── QR result processing ──────────────────────────────────────────────────

    def _process_scan(self) -> None:
        """
        In hardware mode the ESP32 sends "QR:{username}" back which the
        SerialManager would parse and put on the event queue.
        Here we simulate by loading the first stored account.
        """
        self._stop()
        users = storage.list_all_users()
        if users:
            user = User.from_dict(users[0])
            self.app_state.login(user)
            self.app_state.history.clear()
            self.controller.sidebar.refresh()
            self.controller.show_page("dashboard")
        else:
            self.controller.show_alert("Not Found", "No registered account found.")
            self.controller.show_page("home")
