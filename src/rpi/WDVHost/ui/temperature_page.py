import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


_TEMPS = [
    ("❄️  Cold",  "Cold",  C["cold"]),
    ("🌡  Warm",  "Warm",  C["warm"]),
    ("🔥  Hot",   "Hot",   C["hot"]),
]


class TemperaturePage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "Select Temperature").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=PAD, pady=PAD, sticky="nsew")
        body.columnconfigure((0, 1, 2), weight=1)
        body.rowconfigure(0, weight=1)

        for col, (label, value, color) in enumerate(_TEMPS):
            self.make_button(
                body,
                text=label,
                command=lambda v=value: self._select(v),
                color=color,
                height=140,
                font=F["btn_lg"],
            ).grid(row=0, column=col, padx=10, pady=10, sticky="nsew")

        self.make_back_button(self, "services").grid(
            row=2, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def _select(self, temp: str) -> None:
        self.app_state.selection.temperature = temp
        self.controller.show_page("volume")
