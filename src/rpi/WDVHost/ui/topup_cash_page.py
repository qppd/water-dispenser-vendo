import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD
from app_state import CASH_VALUES, REGISTERED_RATES
import hardware_hooks


_COIN_VALUES = [1, 5, 10]        # ≤ ₱10 treated as coins
_BILL_VALUES = [20, 50, 100]     # ≥ ₱20 treated as bills


class TopupCashPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        self.make_heading(self, "Insert Cash").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 4), sticky="w"
        )

        # Live balance display
        self._bal_frame = ctk.CTkFrame(
            self, fg_color=C["dark_blue"], corner_radius=10
        )
        self._bal_frame.grid(row=1, column=0, padx=PAD, pady=4, sticky="ew")
        self._bal_frame.columnconfigure(0, weight=1)

        self._bal_lbl = ctk.CTkLabel(
            self._bal_frame,
            text="Points: 0",
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            text_color=C["accent"],
        )
        self._bal_lbl.grid(row=0, column=0, padx=16, pady=8)

        # Grid of denomination buttons
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.grid(row=2, column=0, padx=PAD, pady=8, sticky="nsew")

        cols = 3
        for col in range(cols):
            grid.columnconfigure(col, weight=1)

        for idx, val in enumerate(CASH_VALUES):
            row_idx, col_idx = divmod(idx, cols)
            is_bill = val >= 20
            color = "#27ae60" if is_bill else C["warning"]

            pts = REGISTERED_RATES.get(val, val)  # shown for registered; guest gets 1:1

            btn = self.make_button(
                grid,
                text=f"₱{val}\n+{pts} pts →",
                command=lambda v=val, b=is_bill: self._insert(v, b),
                color=color,
                text_color=C["white"] if is_bill else "#333333",
                height=BTN_HEIGHT + 10,
                font=F["sub"],
            )
            btn.grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="nsew")

        self.make_back_button(self, "topup_choices").grid(
            row=3, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def on_show(self) -> None:
        self._refresh_balance()
        # Register hardware callbacks so real coin/bill signals also update UI
        self.app_state.register_coin_callback(self._on_hw_insert)
        self.app_state.register_bill_callback(self._on_hw_insert)

    def _refresh_balance(self) -> None:
        self._bal_lbl.configure(
            text=f"Balance: {self.app_state.user.points} pts"
        )

    # ── Hardware event handlers ───────────────────────────────────────────────

    def _on_hw_insert(self, value: int) -> None:
        """Called from main thread via AppState dispatch when hardware fires."""
        pts = self.app_state.add_cash(value)
        self._refresh_balance()
        self.controller.sidebar.refresh()

    # ── Simulation (test button) ──────────────────────────────────────────────

    def _insert(self, value: int, is_bill: bool) -> None:
        if is_bill:
            hardware_hooks.insert_bill(value, self.controller.serial_mgr)
        else:
            hardware_hooks.insert_coin(value, self.controller.serial_mgr)
