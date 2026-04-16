"""
main.py - ABC Splash Kiosk entry point.

Architecture
============
MainApp (CTk)
│
├── sidebar  (Sidebar frame, width=200, left side)        ← persistent on login
│
└── content_host (CTkFrame)                               ← fills remaining width
     └── All page frames stacked; show_page() lifts the active one

Serial events flow:
  SerialManager thread → AppState.hw_event_queue → poll_hw_events() every 50ms
  → AppState.dispatch_coin / dispatch_bill / dispatch_dispense_complete
  → active page callback

Usage
-----
Run on the Raspberry Pi:
    python main.py

Desktop development without hardware:
    python main.py --sim
"""

import sys
import os
import customtkinter as ctk

# ── Ensure this package's directory is on sys.path ───────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app_state import AppState
from serial_manager import SerialManager
from serial_second_esp import SecondESPSerial
from qr_scanner import QRScanner
from thermal_printer import ThermalPrinter
from ui.theme import C, WIN_W, WIN_H, SIDEBAR_W

# ── Import all page classes ───────────────────────────────────────────────────
from ui.home_page            import HomePage
from ui.register_page        import RegisterPage
from ui.login_page           import LoginPage
from ui.forgot_password_page import ForgotPasswordPage
from ui.dashboard_page       import DashboardPage
from ui.profile_page         import ProfilePage
from ui.history_page         import HistoryPage
from ui.services_page        import ServicesPage
from ui.temperature_page     import TemperaturePage
from ui.volume_page          import VolumePage
from ui.topup_choices_page   import TopupChoicesPage
from ui.topup_cash_page      import TopupCashPage
from ui.dispensing_page      import DispensingPage
from ui.qr_scan_page         import QRScanPage
from ui.sidebar              import Sidebar


# ── CustomTkinter appearance ──────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Pages that hide the sidebar (authentication / action screens)
_SIDEBAR_HIDDEN_PAGES = {
    "home", "register", "signin", "forgot", "qr_scan", "dispensing",
}


class MainApp(ctk.CTk):
    """
    Top-level window and page controller.

    Responsibilities
    ----------------
    - Own the single AppState instance
    - Start/stop SerialManager
    - Poll the hardware event queue on the Tk main thread
    - Switch pages via show_page(name)
    - Show modal alerts via show_alert()
    - Expose show_confirm_dispense() called by VolumePage
    """

    def __init__(self, simulation_mode: bool = False) -> None:
        super().__init__()

        self.simulation_mode = simulation_mode

        # ── Window setup ──────────────────────────────────────────────────────
        self.title("ABC Splash Kiosk")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.resizable(False, False)
        self.configure(fg_color=C["app_bg"])

        # Fullscreen kiosk mode
        self.attributes("-fullscreen", True)
        self.config(cursor="none")
        # Allow Escape to exit (remove or comment out for production lockdown)
        self.bind("<Escape>", lambda _e: self._on_close())

        # ── Shared state ──────────────────────────────────────────────────────
        self.app_state = AppState()

        # ── Serial manager ────────────────────────────────────────────────────
        from config import ESP_ACCEPTOR_PORT as _ESP_PORT  # noqa: E402
        port = _ESP_PORT if not simulation_mode else None
        self.serial_mgr = SerialManager(
            event_queue=self.app_state.hw_event_queue,
            port=port,
        )
        self.serial_mgr.start()

        # ── Second ESP32 (ESPWDV) now communicates via ESP-Now through ────────
        # ESPWDVAcceptor. All dispenser commands go through serial_mgr above.
        # SecondESPSerial is kept in simulation mode (port=None) for compatibility.
        self.second_esp = SecondESPSerial(
            event_queue=self.app_state.hw_event_queue,
            port=None,
        )
        self.second_esp.start()

        # ── QR scanner (USB HID keyboard-mode) ────────────────────────────────
        self.qr_scanner = QRScanner(
            event_queue=self.app_state.hw_event_queue,
        )

        # ── Thermal printer ───────────────────────────────────────────────────
        # Priority: PRINTER_PORT env var → config.py → auto-detect.
        # Printer runs independently of simulation_mode (sim only affects ESP32).
        from config import PRINTER_PORT as _CFG_PORT
        _env_port  = os.environ.get("PRINTER_PORT", "").strip()
        _cfg_port  = "" if _CFG_PORT.strip().lower() == "auto" else _CFG_PORT.strip()
        printer_port = _env_port or _cfg_port or ThermalPrinter.detect_port()

        self.printer = ThermalPrinter(port=printer_port)
        if printer_port:
            connected = self.printer.connect()
            if connected:
                print(f"[MainApp] Thermal printer connected on {printer_port}.")
            else:
                print(f"[MainApp] Thermal printer found on {printer_port} but failed to connect.")
        else:
            print("[MainApp] No thermal printer detected – printing disabled.\n"
                  "         Set PRINTER_PORT in config.py or as an env var (e.g. PRINTER_PORT=COM10).")

        # ── Layout: sidebar | content ─────────────────────────────────────────
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.app_state, self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self._content = ctk.CTkFrame(
            self, fg_color=C["screen_bg"], corner_radius=0
        )
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Alert window placeholder
        self._alert_win = None

        # ── Build all pages ───────────────────────────────────────────────────
        self._pages: dict = {}
        self._build_pages()

        # ── Previous-page tracker (used by QRScanPage to go back) ────────────
        self.prev_page: str = "home"

        # ── Start on home ─────────────────────────────────────────────────────
        self.show_page("home")

        # ── QR scanner — must start after window is built ─────────────────────
        self.qr_scanner.start(tk_root=self)

        # ── Hardware event polling ────────────────────────────────────────────
        self._poll_hw_events()

        # ── Clean shutdown ────────────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Page construction ─────────────────────────────────────────────────────

    def _build_pages(self) -> None:
        page_classes = {
            "home":          HomePage,
            "register":      RegisterPage,
            "signin":        LoginPage,
            "forgot":        ForgotPasswordPage,
            "dashboard":     DashboardPage,
            "profile":       ProfilePage,
            "history":       HistoryPage,
            "services":      ServicesPage,
            "temperature":   TemperaturePage,
            "volume":        VolumePage,
            "topup_choices": TopupChoicesPage,
            "topup_cash":    TopupCashPage,
            "dispensing":    DispensingPage,
            "qr_scan":       QRScanPage,
        }
        for name, cls in page_classes.items():
            frame = cls(self._content, self.app_state, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self._pages[name] = frame

    # ── Public navigation API ─────────────────────────────────────────────────

    def show_page(self, name: str) -> None:
        """Raise the named page and call its on_show() lifecycle hook."""
        page = self._pages.get(name)
        if page is None:
            print(f"[MainApp] Unknown page: {name}")
            return

        # Track previous page so pages like QRScanPage can navigate back
        current = getattr(self, "_current_page", "home")
        if current != name:
            self.prev_page = current
        self._current_page = name

        page.tkraise()

        # Toggle sidebar visibility
        if name in _SIDEBAR_HIDDEN_PAGES:
            self.sidebar.grid_remove()
            self._content.grid(
                row=0, column=0, columnspan=2, sticky="nsew"
            )
        else:
            self._content.grid(
                row=0, column=1, columnspan=1, sticky="nsew"
            )
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar.refresh()

        page.on_show()

    # ── Confirm dispense dialog ───────────────────────────────────────────────

    def show_confirm_dispense(self) -> None:
        """Called by VolumePage after volume is chosen."""
        sel  = self.app_state.selection
        temp = sel.temperature if sel.temperature else "N/A"
        msg  = (
            f"Service:       {sel.service}\n"
            f"Temperature:   {temp}\n"
            f"Volume:        {sel.volume_ml} ml\n"
            f"Cost:          {sel.cost_pts} pt{'s' if sel.cost_pts != 1 else ''}\n\n"
            f"Balance after: {self.app_state.user.points - sel.cost_pts} pts\n\n"
            f"💡 Tip: Want to drink directly from the faucet?\n"
            f"   Attach the drinking fountain adapter to the\n"
            f"   tip of the faucet before confirming."
        )
        self.show_alert(
            "Confirm Order",
            msg,
            confirm_text="✅  Confirm",
            confirm_cmd=lambda: self.show_page("dispensing"),
            cancel_text="✗  Cancel",
            cancel_cmd=lambda: self.show_page("volume"),
        )

    # ── Alert dialog ──────────────────────────────────────────────────────────

    def show_alert(
        self,
        title: str,
        message: str,
        confirm_text: str = "OK",
        confirm_cmd=None,
        cancel_text=None,
        cancel_cmd=None,
    ) -> None:
        """Centred modal dialog placed over the kiosk window."""
        if self._alert_win is not None and self._alert_win.winfo_exists():
            self._alert_win.destroy()

        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.update_idletasks()
        dlg.grab_set()

        dlg_w, dlg_h = 420, 320
        x = self.winfo_x() + (WIN_W  - dlg_w) // 2
        y = self.winfo_y() + (WIN_H - dlg_h) // 2
        dlg.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
        dlg.configure(fg_color=C["white"])
        dlg.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dlg,
            text=title,
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=C["dark_blue"],
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 6), sticky="ew")

        ctk.CTkLabel(
            dlg,
            text=message,
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=C["text_dark"],
            wraplength=330,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 14), sticky="ew")

        def _close_and(cmd):
            dlg.destroy()
            if cmd:
                cmd()

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.grid(
            row=2, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="ew"
        )
        btn_row.columnconfigure((0, 1), weight=1)

        if cancel_text:
            ctk.CTkButton(
                btn_row, text=cancel_text,
                command=lambda: _close_and(cancel_cmd),
                fg_color=C["danger"], hover_color="#c0392b",
                text_color=C["white"], height=44, corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
            ).grid(row=0, column=0, padx=4, sticky="ew")

            ctk.CTkButton(
                btn_row, text=confirm_text,
                command=lambda: _close_and(confirm_cmd),
                fg_color=C["accent"], hover_color="#27ae60",
                text_color=C["white"], height=44, corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
            ).grid(row=0, column=1, padx=4, sticky="ew")
        else:
            ctk.CTkButton(
                btn_row, text=confirm_text,
                command=lambda: _close_and(confirm_cmd),
                fg_color=C["dark_blue"], hover_color="#01579b",
                text_color=C["white"], height=44, corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
            ).grid(row=0, column=0, columnspan=2, padx=40, sticky="ew")

        self._alert_win = dlg

    # ── Hardware event polling ────────────────────────────────────────────────

    def _poll_hw_events(self) -> None:
        """
        Drain the HW event queue (populated by SerialManager thread)
        on the Tk main thread.  Scheduled every 50 ms.
        """
        q = self.app_state.hw_event_queue
        while not q.empty():
            try:
                event = q.get_nowait()
            except Exception:
                break

            etype = event.get("type")
            if etype == "coin":
                self.app_state.dispatch_coin(event["value"])
                self.sidebar.refresh()
            elif etype == "bill":
                self.app_state.dispatch_bill(event["value"])
                self.sidebar.refresh()
            elif etype == "dispense_complete":
                self.app_state.dispatch_dispense_complete()
            elif etype == "QR_SCANNED":
                self.app_state.dispatch_qr_scanned(event.get("data", ""))
            elif etype == "temp":
                self.app_state.update_temperature(
                    event.get("sensor", ""), event.get("value", 0.0)
                )
                self.sidebar.refresh_temps()
            elif etype == "water_level":
                present = event.get("present", False)
                self.app_state.update_water_level(present)
                self.sidebar.refresh_water_level()
                # Auto-control inlet solenoid valve (RELAY2):
                # Tank full (100%, present=True)  → close inlet valve (stop filling).
                # Tank not full (50%, present=False) → open inlet valve (allow filling).
                self.serial_mgr.set_inlet_valve(close=present)
            # "raw" / "esp_status" lines are silently ignored here

        self.after(50, self._poll_hw_events)

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.qr_scanner.stop()
        self.serial_mgr.stop()
        self.second_esp.stop()
        self.printer.disconnect()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    sim = "--sim" in sys.argv
    app = MainApp(simulation_mode=sim)
    app.mainloop()


if __name__ == "__main__":
    main()
