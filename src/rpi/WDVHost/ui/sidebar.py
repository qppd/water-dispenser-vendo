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
            text="💧 ABC Splash",
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

        # ── Temperature card ──────────────────────────────────────────────────
        temp_card = ctk.CTkFrame(self, fg_color="#0d3a5c", corner_radius=8)
        temp_card.grid(row=5, column=0, padx=10, pady=(0, 6), sticky="ew")
        temp_card.columnconfigure(0, weight=1)
        temp_card.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            temp_card,
            text="TEMPERATURE",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#b3e5fc",
        ).grid(row=0, column=0, columnspan=2, padx=6, pady=(6, 2))

        # HOT row
        ctk.CTkLabel(
            temp_card,
            text="\U0001f525 HOT",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#ff7043",
        ).grid(row=1, column=0, padx=(8, 2), pady=2, sticky="w")

        self._lbl_temp_hot = ctk.CTkLabel(
            temp_card,
            text="--.-\u00b0C",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#ffccbc",
        )
        self._lbl_temp_hot.grid(row=1, column=1, padx=(2, 8), pady=2, sticky="e")

        # WARM row
        ctk.CTkLabel(
            temp_card,
            text="\U0001f324\ufe0f WARM",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#ffca28",
        ).grid(row=2, column=0, padx=(8, 2), pady=2, sticky="w")

        self._lbl_temp_warm = ctk.CTkLabel(
            temp_card,
            text="--.-\u00b0C",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#fff9c4",
        )
        self._lbl_temp_warm.grid(row=2, column=1, padx=(2, 8), pady=2, sticky="e")

        # COLD row
        ctk.CTkLabel(
            temp_card,
            text="\u2744\ufe0f COLD",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#4fc3f7",
        ).grid(row=3, column=0, padx=(8, 2), pady=(2, 6), sticky="w")

        self._lbl_temp_cold = ctk.CTkLabel(
            temp_card,
            text="--.-\u00b0C",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#b3e5fc",
        )
        self._lbl_temp_cold.grid(row=3, column=1, padx=(2, 8), pady=(2, 6), sticky="e")

        # ── Water level card ──────────────────────────────────────────────────
        wl_card = ctk.CTkFrame(self, fg_color="#0d3a5c", corner_radius=8)
        wl_card.grid(row=6, column=0, padx=10, pady=(0, 6), sticky="ew")
        wl_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wl_card,
            text="💧 TANK LEVEL",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#b3e5fc",
        ).grid(row=0, column=0, padx=6, pady=(6, 2))

        self._wl_bar = ctk.CTkProgressBar(
            wl_card,
            orientation="horizontal",
            height=10,
            corner_radius=5,
            progress_color="#4fc3f7",
            fg_color="#1d4570",
        )
        self._wl_bar.set(0.5)
        self._wl_bar.grid(row=1, column=0, padx=8, pady=(0, 2), sticky="ew")

        self._lbl_wl = ctk.CTkLabel(
            wl_card,
            text="--",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color="#b3e5fc",
        )
        self._lbl_wl.grid(row=2, column=0, padx=6, pady=(0, 6))

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
        ).grid(row=7, column=0, padx=10, pady=(0, 20), sticky="ew")

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Sync user labels from current app state."""
        u = self.app_state.user
        self._lbl_user.configure(text=u.username)
        self._lbl_email.configure(text=u.email)
        self._lbl_pts.configure(text=str(u.points))

    def refresh_temps(self) -> None:
        """Update temperature labels from app_state.temperatures."""
        temps = self.app_state.temperatures

        def _fmt(val) -> str:
            return f"{val:.1f}\u00b0C" if val is not None else "--.-\u00b0C"

        self._lbl_temp_hot.configure(text=_fmt(temps.get("HOT")))
        self._lbl_temp_warm.configure(text=_fmt(temps.get("WARM")))
        self._lbl_temp_cold.configure(text=_fmt(temps.get("COLD")))

    def refresh_water_level(self) -> None:
        """Update the tank level bar and label from app_state.water_level_present."""
        present = self.app_state.water_level_present
        if present is None:
            self._wl_bar.set(0.5)
            self._wl_bar.configure(progress_color="#78909c")
            self._lbl_wl.configure(text="-- (waiting...)", text_color="#b3e5fc")
        elif present:
            self._wl_bar.set(1.0)
            self._wl_bar.configure(progress_color="#4fc3f7")
            self._lbl_wl.configure(text="100%  \u2713 FULL", text_color="#4fc3f7")
        else:
            self._wl_bar.set(0.5)
            self._wl_bar.configure(progress_color="#ffb300")
            self._lbl_wl.configure(text="50%  \u26a0 FILLING", text_color="#ffb300")

    # ── Private ───────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        self.app_state.logout()
        self.controller.show_page("home")
