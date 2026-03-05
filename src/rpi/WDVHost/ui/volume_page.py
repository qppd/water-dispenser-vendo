"""
ui/volume_page.py - Volume selection with per-user pricing (page-volume).

Renders buttons dynamically based on whether the user is a guest or
registered account.  Shows points balance and cost per option so the
user can make an informed choice.
"""

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD
from app_state import PRICING_REGISTERED, PRICING_GUEST


class VolumePage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)   # balance row
        self.rowconfigure(2, weight=1)   # buttons row

        self._heading = self.make_heading(self, "Select Volume")
        self._heading.grid(row=0, column=0, padx=PAD, pady=(PAD, 4), sticky="w")

        # Points balance hint
        self._bal_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(*F["sub"]),
            text_color=C["accent"],
        )
        self._bal_lbl.grid(row=1, column=0, padx=PAD, pady=(0, 6), sticky="w")

        # Button container (rebuilt on each show)
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.grid(row=2, column=0, padx=PAD, pady=4, sticky="nsew")

        self.make_back_button(self, "services").grid(
            row=3, column=0, padx=PAD, pady=(4, PAD), sticky="w"
        )

    def on_show(self) -> None:
        sel = self.app_state.selection
        temp_str = f" ({sel.temperature})" if sel.temperature else ""
        svc_str  = "Fountain Volume" if sel.service == "Fountain" else f"Volume{temp_str}"
        self._heading.configure(text=svc_str)
        self._bal_lbl.configure(text=f"Your balance: {self.app_state.user.points} pts")

        # Rebuild buttons
        for w in self._container.winfo_children():
            w.destroy()

        pricing = PRICING_GUEST if self.app_state.user.is_guest else PRICING_REGISTERED

        self._container.columnconfigure((0, 1), weight=1)
        self._container.rowconfigure((0, 1), weight=1)

        for idx, item in enumerate(pricing):
            row, col = divmod(idx, 2)
            ml, cost = item["ml"], item["cost"]
            can_afford = self.app_state.user.points >= cost
            color = C["aqua"] if can_afford else "#aaaaaa"

            btn = self.make_button(
                self._container,
                text=f"{ml} ml\n{cost} pt{'s' if cost != 1 else ''}",
                command=lambda m=ml, c=cost: self._select(m, c),
                color=color,
                height=100,
                font=F["btn_lg"],
            )
            if not can_afford:
                btn.configure(state="disabled")
            btn.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    def _select(self, ml: int, cost: int) -> None:
        if self.app_state.user.points < cost:
            self.controller.show_alert("Insufficient Points", "Please top up first.")
            return
        self.app_state.selection.volume_ml  = ml
        self.app_state.selection.cost_pts   = cost
        self.controller.show_confirm_dispense()
