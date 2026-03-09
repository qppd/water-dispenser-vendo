import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD


class HistoryPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.make_heading(self, "Transaction History").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="w"
        )

        # Scrollable container
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=C["white"], corner_radius=10
        )
        self._scroll.grid(row=1, column=0, padx=PAD, pady=4, sticky="nsew")
        self._scroll.columnconfigure(0, weight=1)
        self._scroll.columnconfigure(1, weight=0)

        self._empty_lbl = ctk.CTkLabel(
            self._scroll,
            text="No transactions yet.",
            font=ctk.CTkFont(*F["body"]),
            text_color=C["steel"],
        )
        self._empty_lbl.grid(row=0, column=0, columnspan=2, pady=30)

        self.make_back_button(self, "dashboard").grid(
            row=2, column=0, padx=PAD, pady=(4, PAD), sticky="w"
        )

    def on_show(self) -> None:
        # Clear and rebuild the list
        for child in self._scroll.winfo_children():
            child.destroy()

        txns = self.app_state.history
        if not txns:
            self._empty_lbl = ctk.CTkLabel(
                self._scroll,
                text="No transactions yet.",
                font=ctk.CTkFont(*F["body"]),
                text_color=C["steel"],
            )
            self._empty_lbl.grid(row=0, column=0, columnspan=3, pady=30)
            return

        # Header row
        for col, txt in enumerate(["Time", "Description", "Points"]):
            ctk.CTkLabel(
                self._scroll,
                text=txt,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                text_color=C["dark_blue"],
            ).grid(row=0, column=col, padx=8, pady=4, sticky="w")

        # Divider
        ctk.CTkFrame(
            self._scroll, height=1, fg_color=C["aqua"]
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=2)

        for idx, txn in enumerate(txns):
            row = idx + 2
            color = C["accent"] if txn.points_delta > 0 else C["danger"]
            sign  = "+" if txn.points_delta > 0 else ""

            ctk.CTkLabel(
                self._scroll,
                text=txn.timestamp,
                font=ctk.CTkFont(*F["small"]),
                text_color=C["steel"],
            ).grid(row=row, column=0, padx=8, pady=2, sticky="w")

            ctk.CTkLabel(
                self._scroll,
                text=txn.description,
                font=ctk.CTkFont(*F["body"]),
                text_color=C["text_dark"],
            ).grid(row=row, column=1, padx=8, pady=2, sticky="w")

            ctk.CTkLabel(
                self._scroll,
                text=f"{sign}{txn.points_delta} pt",
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
                text_color=color,
            ).grid(row=row, column=2, padx=8, pady=2, sticky="e")

            # Thin separator
            if idx < len(txns) - 1:
                ctk.CTkFrame(
                    self._scroll, height=1, fg_color="#e1f5fe"
                ).grid(row=row + 1000, column=0, columnspan=3, sticky="ew", padx=4)
