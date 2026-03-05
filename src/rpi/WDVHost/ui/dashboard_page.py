"""
ui/dashboard_page.py - Main menu shown after login (page-menu).

Four large tiles: Profile · History · Services · Top-Up
"""

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


class DashboardPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "Dashboard").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.grid(row=1, column=0, padx=PAD, pady=PAD, sticky="nsew")
        grid.columnconfigure((0, 1), weight=1)
        grid.rowconfigure((0, 1), weight=1)

        tiles = [
            ("👤  Profile",           C["dark_blue"],  "profile",       0, 0),
            ("📜  Transaction History", C["dark_blue"], "history",       0, 1),
            ("💧  Water Services",     C["aqua"],       "services",      1, 0),
            ("₱   Top Up",            C["accent"],     "topup_choices", 1, 1),
        ]

        for text, color, page, row, col in tiles:
            self.make_button(
                grid, text,
                command=lambda p=page: self.controller.show_page(p),
                color=color,
                height=120,
                font=F["btn_lg"],
            ).grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    def on_show(self) -> None:
        self.controller.sidebar.refresh()
