"""
ui/sidebar.py - Persistent left-hand panel visible after login.

Displays: user name · points balance · logout button.
MainApp calls sidebar.refresh() whenever user state changes.
"""

from __future__ import annotations

import customtkinter as ctk
from typing import TYPE_CHECKING

from ui.theme import C, F, SIDEBAR_W, BTN_HEIGHT, BTN_CORNER

if TYPE_CHECKING:
    from app_state import AppState


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app_state: "AppState", controller) -> None:
        super().__init__(
            parent,
            width=SIDEBAR_W,
            fg_color=C["sidebar_bg"],
            corner_radius=0,
        )
        self.app_state  = app_state
        self.controller = controller
        self._build()

    def _build(self) -> None:
        self.grid_propagate(False)
        self.columnconfigure(0, weight=1)

        # ── App logo / title ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="💧 AquaSmart",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=C["white"],
        ).grid(row=0, column=0, padx=10, pady=(20, 4), sticky="ew")

        ctk.CTkFrame(self, height=1, fg_color="#4fc3f7").grid(
            row=1, column=0, padx=10, pady=4, sticky="ew"
        )

        # ── User info card ────────────────────────────────────────────────────
        card = ctk.CTkFrame(self, fg_color="#2a5580", corner_radius=8)
        card.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
        card.columnconfigure(0, weight=1)

        self._lbl_user = ctk.CTkLabel(
            card,
            text="Guest",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=C["white"],
        )
        self._lbl_user.grid(row=0, column=0, padx=8, pady=(8, 2), sticky="w")

        self._lbl_email = ctk.CTkLabel(
            card,
            text="---",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color="#b3e5fc",
        )
        self._lbl_email.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="w")

        # ── Points balance ────────────────────────────────────────────────────
        pts_card = ctk.CTkFrame(
            self, fg_color="#1d4570", corner_radius=8,
            border_color="#4fc3f7", border_width=2,
        )
        pts_card.grid(row=3, column=0, padx=10, pady=6, sticky="ew")
        pts_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pts_card,
            text="POINTS",
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color="#e1f5fe",
        ).grid(row=0, column=0, padx=6, pady=(6, 0))

        self._lbl_pts = ctk.CTkLabel(
            pts_card,
            text="0",
            font=ctk.CTkFont("Segoe UI", 30, "bold"),
            text_color=C["accent"],
        )
        self._lbl_pts.grid(row=1, column=0, padx=6, pady=(0, 6))

        # ── Spacer ────────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color="transparent").grid(
            row=4, column=0, sticky="nsew"
        )
        self.rowconfigure(4, weight=1)

        # ── Logout button ─────────────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="Logout",
            command=self._logout,
            fg_color=C["danger"],
            hover_color="#c0392b",
            text_color=C["white"],
            height=44,
            corner_radius=BTN_CORNER,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
        ).grid(row=5, column=0, padx=10, pady=(0, 20), sticky="ew")

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Sync labels from current app state."""
        u = self.app_state.user
        self._lbl_user.configure(text=u.username)
        self._lbl_email.configure(text=u.email)
        self._lbl_pts.configure(text=str(u.points))

    # ── Private ───────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        self.app_state.logout()
        self.controller.show_page("home")
