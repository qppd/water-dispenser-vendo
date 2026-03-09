from __future__ import annotations

import customtkinter as ctk
from typing import TYPE_CHECKING

from ui.theme import C, F, BTN_HEIGHT, BTN_CORNER, PAD

if TYPE_CHECKING:
    from app_state import AppState


class BasePage(ctk.CTkFrame):
    def __init__(self, parent, app_state: "AppState", controller) -> None:
        super().__init__(parent, fg_color=C["screen_bg"], corner_radius=0)
        self.app_state  = app_state
        self.controller = controller
        self.build()

    def build(self) -> None:
        raise NotImplementedError

    def on_show(self) -> None:
        """Override in subclass to refresh dynamic content each time shown."""

    def make_button(
        self,
        parent,
        text: str,
        command,
        color: str = C["aqua"],
        text_color: str = C["white"],
        height: int = BTN_HEIGHT,
        corner_radius: int = BTN_CORNER,
        font=F["btn"],
        **kwargs,
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=color,
            hover_color=self._darken(color),
            text_color=text_color,
            height=height,
            corner_radius=corner_radius,
            font=ctk.CTkFont(*font),
            **kwargs,
        )

    def make_label(
        self,
        parent,
        text: str,
        font=F["body"],
        text_color: str = C["text_dark"],
        **kwargs,
    ) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(*font),
            text_color=text_color,
            **kwargs,
        )

    def make_entry(
        self,
        parent,
        placeholder: str = "",
        show: str = "",
        **kwargs,
    ) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show=show,
            height=42,
            font=ctk.CTkFont(*F["body"]),
            border_color=C["aqua"],
            fg_color=C["white"],
            text_color=C["text_dark"],
            **kwargs,
        )

    def make_heading(self, parent, text: str) -> ctk.CTkLabel:
        return self.make_label(parent, text, font=F["heading"], text_color=C["dark_blue"])

    def make_back_button(self, parent, target_page: str) -> ctk.CTkButton:
        return self.make_button(
            parent,
            text="← Back",
            command=lambda: self.controller.show_page(target_page),
            color=C["btn_back"],
            height=40,
            font=F["small"],
        )

    @staticmethod
    def _darken(hex_color: str) -> str:
        """Return a slightly darker version of a hex colour for hover state."""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color
