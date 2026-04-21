import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, BTN_WIDE, PAD
from app_state import ACTIVATION_FEE, WELCOME_BONUS
import storage
from firebase_config import fb_auth


class RegisterPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Centered card ──────────────────────────────────────────────────────
        card = ctk.CTkFrame(
            self,
            fg_color=C["white"],
            corner_radius=16,
            border_color=C["aqua"],
            border_width=2,
        )
        card.grid(row=0, column=0, padx=50, pady=20, sticky="")
        card.columnconfigure(0, weight=1)

        self.make_heading(card, "Account Setup").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="ew"
        )

        # Fee notice
        self._notice_var = ctk.StringVar(value=f"₱{ACTIVATION_FEE} activation fee required")
        self._notice_lbl = ctk.CTkLabel(
            card,
            textvariable=self._notice_var,
            font=ctk.CTkFont(*F["small"]),
            text_color=C["danger"],
        )
        self._notice_lbl.grid(row=1, column=0, padx=PAD, pady=(0, 6))

        # ── Form fields ────────────────────────────────────────────────────────
        self._e_user  = self.make_entry(card, placeholder="Enter your username", width=300)
        self._e_email = self.make_entry(card, placeholder="Enter your email", width=300)
        self._e_phone = self.make_entry(card, placeholder="Enter your phone number", width=300)
        self._e_pass  = self.make_entry(
            card, placeholder="Enter your password", show="\u25cf", width=300
        )

        for idx, widget in enumerate(
            [self._e_user, self._e_email, self._e_phone, self._e_pass], start=2
        ):
            widget.grid(row=idx, column=0, padx=PAD, pady=4, sticky="ew")

        # Confirm button (starts disabled)
        self._btn_confirm = self.make_button(
            card,
            text="✅  Confirm Activation",
            command=self._complete_registration,
            color=C["accent"],
            height=BTN_HEIGHT,
        )
        self._btn_confirm.configure(state="disabled", fg_color="#cccccc")
        self._btn_confirm.grid(row=6, column=0, padx=PAD, pady=(10, PAD), sticky="ew")

        # Back
        self.make_back_button(self, "home").grid(
            row=1, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    # ── on_show: reset state every visit ──────────────────────────────────────

    def on_show(self) -> None:
        # Always reset to a clean Guest user so leftover points from a
        # previous abandoned registration (or hardware noise) can't persist.
        self.app_state.user.points = 0
        self.app_state.reset_activation_cash()
        self._update_notice()
        self._btn_confirm.configure(state="disabled", fg_color="#cccccc")
        # Register coin/bill callbacks so live hardware also works
        self.app_state.register_coin_callback(self._on_hw_coin)
        self.app_state.register_bill_callback(self._on_hw_bill)

    # ── Hardware callbacks ────────────────────────────────────────────────────

    def _on_hw_coin(self, value: int) -> None:
        """Accept any coin denomination, accumulate toward the activation fee."""
        self._sim_coin(value)

    def _on_hw_bill(self, value: int) -> None:
        """Accept bills too (e.g. user inserts ₱20 to cover ₱10 fee)."""
        self._sim_coin(value)

    def _sim_coin(self, value: int) -> None:
        self.app_state.add_cash(value, is_activation=True)
        self._update_notice()
        self.controller.sidebar.refresh()

    def _update_notice(self) -> None:
        inserted = self.app_state.activation_cash_inserted()
        if inserted >= ACTIVATION_FEE:
            self._notice_var.set(f"✅ Payment received (₱{inserted})")
            self._notice_lbl.configure(text_color=C["accent"])
            self._btn_confirm.configure(state="normal", fg_color=C["accent"])
        else:
            needed = ACTIVATION_FEE - inserted
            self._notice_var.set(f"₱{ACTIVATION_FEE} required — ₱{needed} still needed")
            self._notice_lbl.configure(text_color=C["danger"])
            self._btn_confirm.configure(state="disabled", fg_color="#cccccc")

    # ── Register ──────────────────────────────────────────────────────────────

    def _complete_registration(self) -> None:
        inserted = self.app_state.activation_cash_inserted()
        if inserted < ACTIVATION_FEE:
            return

        username = self._e_user.get().strip() or "User"
        email    = self._e_email.get().strip()
        phone    = self._e_phone.get().strip() or "---"
        password = self._e_pass.get()

        if not password:
            self.controller.show_alert("Missing Password", "Please enter a password.")
            return

        if not email or "@" not in email:
            self.controller.show_alert("Missing Email", "Please enter a valid email address.")
            return

        # Calculate final balance explicitly:
        #   change (overpayment refunded as points) + welcome bonus.
        # Activation cash was tracked separately in _activation_cash and was
        # NEVER added to user.points, so points must be set here, not adjusted.
        change       = inserted - ACTIVATION_FEE
        final_points = WELCOME_BONUS + change

        try:
            # ── Step 1: Create Firebase Auth account using real email ─────────
            result = fb_auth.create_user_with_email_and_password(email, password)
            uid    = result["localId"]
            self.app_state.user.uid = uid

            # ── Step 2: Apply profile fields and mark as registered ───────────
            self.app_state.user.username = username
            self.app_state.user.email    = email
            self.app_state.user.phone    = phone
            self.app_state.user.is_guest = False

            # ── Step 3: Set points explicitly (clean, no partial state risk) ──
            self.app_state.user.points = final_points

            # Record accounting transactions in history
            self.app_state.add_transaction("Activation Fee", -ACTIVATION_FEE)
            self.app_state.add_transaction("Welcome Bonus", WELCOME_BONUS)
            if change > 0:
                self.app_state.add_transaction(f"Overpayment change ₱{change}", change)

            # ── Step 4: Save profile to RTDB (password stripped by storage.py) ─
            storage.save_user(self.app_state.user.to_dict())

        except Exception as exc:
            # Roll back in-memory state fully on Firebase failure
            self.app_state.user.points = 0
            self.controller.show_alert(
                "Registration Failed",
                f"Could not create account:\n{exc}",
            )
            return

        self.controller.show_alert(
            "Success! 🎉",
            f"Account created for {username}.\nYou have {self.app_state.user.points} points.",
        )
        self.controller.sidebar.refresh()
        self.app_state.clear_callbacks()
        self.controller.show_page("home")
