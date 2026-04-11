from __future__ import annotations
from typing import Optional

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, PAD
import hardware_hooks


_COUNTDOWN_START = 3     # seconds
_POLL_MS         = 100   # how often to advance the progress bar


class DispensingPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(list(range(6)), weight=0)
        center.rowconfigure(6, weight=1)

        # Instruction label  e.g. "Place your bottle under the nozzle…"
        self._instr_lbl = ctk.CTkLabel(
            center,
            text="Get ready…",
            font=ctk.CTkFont(*F["heading"]),
            text_color=C["dark_blue"],
        )
        self._instr_lbl.grid(row=0, column=0, pady=(60, 10))

        # Big countdown number
        self._countdown_lbl = ctk.CTkLabel(
            center,
            text="3",
            font=ctk.CTkFont(*F["count"]),
            text_color=C["dark_blue"],
        )
        self._countdown_lbl.grid(row=1, column=0, pady=10)

        # Service/volume summary
        self._summary_lbl = ctk.CTkLabel(
            center,
            text="",
            font=ctk.CTkFont(*F["body"]),
            text_color=C["steel"],
        )
        self._summary_lbl.grid(row=2, column=0, pady=4)

        # Progress bar (hidden during countdown)
        self._progress = ctk.CTkProgressBar(
            center,
            width=400,
            height=20,
            progress_color=C["aqua"],
            fg_color="#d0eaf8",
        )
        self._progress.set(0)
        self._progress.grid(row=3, column=0, pady=10)
        self._progress.grid_remove()  # hidden until countdown finishes

        # Status label during dispensing
        self._status_lbl = ctk.CTkLabel(
            center, text="", font=ctk.CTkFont(*F["sub"]), text_color=C["accent"]
        )
        self._status_lbl.grid(row=4, column=0, pady=4)

        # Cancel button (emergency stop)
        self._cancel_btn = self.make_button(
            center, "⛔  Emergency Stop",
            command=self._emergency_stop,
            color=C["danger"],
            height=44,
            font=F["btn"],
        )
        self._cancel_btn.grid(row=5, column=0, pady=10)

        self._job_countdown: Optional[str] = None
        self._job_progress:  Optional[str] = None
        self._finished:       bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        self._finished = False
        sel = self.app_state.selection
        svc  = sel.service
        temp = sel.temperature
        ml   = sel.volume_ml
        cost = sel.cost_pts

        summary = f"{svc}  •  {temp}  •  {ml} ml  •  {cost} pt{'s' if cost != 1 else ''}"
        self._summary_lbl.configure(text=summary)

        if svc == "Dispense":
            self._instr_lbl.configure(text="Place your bottle under the nozzle…")
        else:
            self._instr_lbl.configure(text="Move close to the fountain nozzle…")

        self._countdown_lbl.configure(text=str(_COUNTDOWN_START))
        self._progress.grid_remove()
        self._status_lbl.configure(text="")

        # Register dispense_complete hardware callback
        self.app_state.register_dispense_complete_callback(self._on_hw_complete)

        self._start_countdown(_COUNTDOWN_START)

    # ── Countdown ────────────────────────────────────────────────────────────

    def _start_countdown(self, count: int) -> None:
        self._countdown_lbl.configure(text=str(count))
        if count > 0:
            self._job_countdown = self.after(
                1000, self._start_countdown, count - 1
            )
        else:
            self._countdown_lbl.configure(text="")
            self._begin_dispensing()

    # ── Dispensing ────────────────────────────────────────────────────────────

    def _begin_dispensing(self) -> None:
        sel = self.app_state.selection

        # Deduct points — AppState._sync_points_async() handles Firebase RTDB update
        ok = self.app_state.deduct_points(
            sel.cost_pts,
            f"{sel.service} {sel.volume_ml}ml {sel.temperature}",
        )
        if not ok:
            self.controller.show_alert("Insufficient Points", "Not enough points.")
            self.controller.show_page("volume")
            return

        self.controller.sidebar.refresh()

        # Send hardware command
        self._duration_ms = hardware_hooks.start_dispense(
            sel.service,
            sel.temperature,
            sel.volume_ml,
            self.controller.serial_mgr,
        )

        self._instr_lbl.configure(text="Dispensing…")
        self._status_lbl.configure(text="💧 Please wait…")
        self._progress.set(0)
        self._progress.grid()

        self._elapsed_ms = 0
        self._tick_progress()

    def _tick_progress(self) -> None:
        self._elapsed_ms += _POLL_MS
        ratio = min(self._elapsed_ms / max(self._duration_ms, 1), 1.0)
        self._progress.set(ratio)

        if self._elapsed_ms >= self._duration_ms:
            self._finish()
        else:
            self._job_progress = self.after(_POLL_MS, self._tick_progress)

    # ── Completion ────────────────────────────────────────────────────────────

    def _on_hw_complete(self) -> None:
        """Called from main thread when ESP32 sends 'Dispensed water'."""
        self._cancel_pending_jobs()
        self._finish()

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._cancel_pending_jobs()
        self.app_state.clear_callbacks()
        self._progress.set(1.0)
        self._status_lbl.configure(text="✅ Done!")
        self.after(800, self._show_done_dialog)

    def _show_done_dialog(self) -> None:
        sel = self.app_state.selection

        # Print receipt on thermal printer (background thread — non-blocking)
        from datetime import datetime
        txn = {
            "transaction_id": datetime.now().strftime("TXN-%Y%m%d-%H%M%S"),
            "credit": sel.cost_pts,
            "volume_ml": sel.volume_ml,
            "service": sel.service,
            "temperature": sel.temperature if sel.temperature else "N/A",
        }
        hardware_hooks.print_receipt(txn, printer=self.controller.printer)

        self.controller.show_alert(
            "Complete! 💧",
            f"Dispensed {sel.volume_ml} ml.\nRemaining points: {self.app_state.user.points}",
        )
        self.controller.show_page("dashboard")

    # ── Emergency stop ─────────────────────────────────────────────────────────

    def _emergency_stop(self) -> None:
        self._cancel_pending_jobs()
        hardware_hooks.stop_dispense(self.controller.serial_mgr)
        self.app_state.clear_callbacks()
        self.controller.show_alert("Stopped", "Dispense halted.")
        self.controller.show_page("dashboard")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _cancel_pending_jobs(self) -> None:
        if self._job_countdown:
            self.after_cancel(self._job_countdown)
            self._job_countdown = None
        if self._job_progress:
            self.after_cancel(self._job_progress)
            self._job_progress = None
