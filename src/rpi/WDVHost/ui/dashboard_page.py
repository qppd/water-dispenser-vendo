import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


class DashboardPage(BasePage):

    def build(self) -> None:
        self._temp_refresh_id = None
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
            ("💧  Water Services",     C["aqua"],       "temperature",   1, 0),
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
        self.controller.sidebar.refresh_temps()
        self.controller.sidebar.refresh_water_level()
        self._schedule_temp_refresh()

    def _schedule_temp_refresh(self) -> None:
        """Cancel any pending timer and arm a new 10-second periodic refresh."""
        if self._temp_refresh_id is not None:
            try:
                self.after_cancel(self._temp_refresh_id)
            except Exception:
                pass
        self._temp_refresh_id = self.after(10_000, self._periodic_temp_refresh)

    def _periodic_temp_refresh(self) -> None:
        """Non-blocking 10-second periodic temperature refresh for the sidebar."""
        self._temp_refresh_id = None
        if getattr(self.controller, "_current_page", "") != "dashboard":
            return
        self.controller.sidebar.refresh_temps()
        self._temp_refresh_id = self.after(10_000, self._periodic_temp_refresh)
