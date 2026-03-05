"""
ui/topup_choices_page.py - Top-up method selection (page-topup-choices).
"""

import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


class TopupChoicesPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "Top Up Method").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=PAD, pady=PAD, sticky="nsew")
        body.columnconfigure((0, 1), weight=1)
        body.rowconfigure(0, weight=1)

        self.make_button(
            body,
            text="🪙  Coins & Bills\n\nInsert cash",
            command=lambda: self.controller.show_page("topup_cash"),
            color=C["dark_blue"],
            height=140,
            font=F["btn_lg"],
        ).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.make_button(
            body,
            text="💳  Other Methods\n\n(Coming soon)",
            command=lambda: self.controller.show_alert(
                "Unavailable", "Only cash top-up is currently supported."
            ),
            color=C["btn_back"],
            height=140,
            font=F["btn_lg"],
        ).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.make_back_button(self, "dashboard").grid(
            row=2, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )
