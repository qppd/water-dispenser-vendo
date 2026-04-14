import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


class ServicesPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "Choose Service").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=PAD, pady=PAD, sticky="nsew")
        body.columnconfigure((0, 1), weight=1)
        body.rowconfigure(0, weight=1)

        # Water Dispenser tile
        self.make_button(
            body,
            text="🫙  Water Dispenser\n\nFill your bottle",
            command=self._select_dispenser,
            color=C["dark_blue"],
            height=160,
            font=F["btn_lg"],
        ).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Drinking Fountain tile
        self.make_button(
            body,
            text="⛲  Drinking Fountain\n\nDrink directly",
            command=self._select_fountain,
            color=C["aqua"],
            height=160,
            font=F["btn_lg"],
        ).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.make_back_button(self, "dashboard").grid(
            row=2, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def _select_dispenser(self) -> None:
        self.app_state.selection.service = "Dispense"
        self.controller.show_page("temperature")

    def _select_fountain(self) -> None:
        self.app_state.selection.service = "Fountain"
        self.controller.show_page("temperature")
