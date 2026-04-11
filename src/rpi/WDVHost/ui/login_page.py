import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, BTN_WIDE, PAD
from app_state import User
from firebase_config import fb_auth
import storage


class LoginPage(BasePage):

    def build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self,
            fg_color=C["white"],
            corner_radius=16,
            border_color=C["aqua"],
            border_width=2,
        )
        card.grid(row=0, column=0, padx=100, pady=30, sticky="")
        card.columnconfigure(0, weight=1)

        self.make_heading(card, "Sign In").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 12), sticky="ew"
        )

        self._e_user = self.make_entry(card, placeholder="Username")
        self._e_pass = self.make_entry(card, placeholder="Password", show="●")

        self._e_user.grid(row=1, column=0, padx=PAD, pady=6, sticky="ew")
        self._e_pass.grid(row=2, column=0, padx=PAD, pady=6, sticky="ew")

        self.make_button(
            card, "Login",
            command=self._login,
            color=C["dark_blue"],
            height=BTN_HEIGHT,
        ).grid(row=3, column=0, padx=PAD, pady=(10, 4), sticky="ew")

        ctk.CTkLabel(
            card,
            text="Forgot Password?",
            font=ctk.CTkFont(*F["small"]),
            text_color=C["dark_blue"],
            cursor="hand2",
        ).grid(row=4, column=0, padx=PAD, pady=(4, PAD))
        card.winfo_children()[-1].bind(
            "<Button-1>", lambda _: self.controller.show_page("forgot")
        )

        self.make_back_button(self, "home").grid(
            row=1, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def on_show(self) -> None:
        self._e_user.delete(0, "end")
        self._e_pass.delete(0, "end")

    def _login(self) -> None:
        username = self._e_user.get().strip()
        password = self._e_pass.get()

        if not username or not password:
            self.controller.show_alert("Login Failed", "Please enter username and password.")
            return

        try:
            # ── Step 1: Look up username → get real email from RTDB ───────────
            data = storage.load_user(username)
            if not data:
                self.controller.show_alert("Not Found", "No account with that username.")
                return

            email = data.get("email", "")
            if not email or email == "---" or "@" not in email:
                self.controller.show_alert(
                    "Login Failed",
                    "No email linked to this account. Contact support.",
                )
                return

            # ── Step 2: Authenticate via Firebase Auth with real email ─────────
            result = fb_auth.sign_in_with_email_and_password(email, password)
            uid    = result["localId"]

            data["uid"] = uid
            user = User.from_dict(data)
            self.app_state.login(user)
            self.app_state.history.clear()
            self.controller.sidebar.refresh()
            self.controller.show_page("dashboard")

        except Exception:
            self.controller.show_alert("Login Failed", "Invalid username or password.")
