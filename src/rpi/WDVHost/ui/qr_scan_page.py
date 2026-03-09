from __future__ import annotations
from typing import Optional

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, PAD
from app_state import User
import storage
import hardware_hooks

# Idle timeout — if no QR is scanned within this period, go back to previous page.
_IDLE_TIMEOUT_MS = 30_000


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
            command=self._cancel,
            color=C["btn_back"],
            height=40,
            font=F["small"],
        ).grid(row=3, column=0, pady=20)

        self._scan_box   = scan_outer
        self._bar_y      = 0
        self._bar_dir    = 1
        self._anim_job: Optional[str] = None
        self._scan_job:  Optional[str] = None
        self._got_scan:  bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        self._got_scan = False

        # Send trigger to ESP32-attached QR reader (if any)
        hardware_hooks.scan_qr(self.controller.serial_mgr)

        # Register for QR_SCANNED events from the USB HID scanner
        self.app_state.register_qr_callback(self._on_qr_scanned)

        self._bar_y   = 0
        self._bar_dir = 1
        self._animate_bar()

        # After 30 s with no scan, silently return to the previous page.
        self._scan_job = self.after(_IDLE_TIMEOUT_MS, self._on_timeout)

    def _cancel(self) -> None:
        self._stop()
        self.app_state.register_qr_callback(None)
        self.controller.show_page("home")

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

    # ── QR event callback (from USB HID scanner via AppState) ─────────────────

    def _on_qr_scanned(self, data: str) -> None:
        """
        Called on the main thread when a QR_SCANNED event is dispatched.

        Expected data formats:
            USER:<username>
            PAY:<amount>
            TXN:<transaction_id>
        """
        if self._got_scan:
            return
        self._got_scan = True
        self._stop()
        self.app_state.register_qr_callback(None)

        # Parse the QR data
        if data.startswith("USER:"):
            username = data[5:].strip()
            self._login_by_username(username)
        else:
            # Treat raw data as a username lookup
            self._login_by_username(data.strip())

    def _login_by_username(self, username: str) -> None:
        """Look up the user by username and log in."""
        user_dict = storage.load_user(username)
        if user_dict:
            user = User.from_dict(user_dict)
            self.app_state.login(user)
            self.app_state.history.clear()
            self.controller.sidebar.refresh()
            self.controller.show_page("dashboard")
        else:
            # Stay on this page — let the user try again or cancel.
            self._got_scan = False
            self.controller.show_alert(
                "Not Found",
                f"No account found for \"{username}\".\nPlease try again or press Cancel.",
            )
            # Restart the idle timeout after alert is dismissed.
            if self._scan_job:
                self.after_cancel(self._scan_job)
            self._scan_job = self.after(_IDLE_TIMEOUT_MS, self._on_timeout)

    # ── Idle timeout ──────────────────────────────────────────────────────────

    def _on_timeout(self) -> None:
        """Called after 30 s of no scan — go back to the page we came from."""
        if self._got_scan:
            return
        self._stop()
        self.app_state.register_qr_callback(None)
        prev = getattr(self.controller, "prev_page", "home")
        self.controller.show_page(prev)
