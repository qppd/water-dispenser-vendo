import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD
from firebase_config import fb_auth


class ForgotPasswordPage(BasePage):

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
        card.grid(row=0, column=0, padx=100, pady=40, sticky="")
        card.columnconfigure(0, weight=1)

        self.make_heading(card, "Reset Password").grid(
            row=0, column=0, padx=PAD, pady=(PAD, 6), sticky="ew"
        )

        ctk.CTkLabel(
            card,
            text="Enter your registered email. A reset link will be sent to your inbox.",
            font=ctk.CTkFont(*F["small"]),
            text_color=C["steel"],
            wraplength=280,
        ).grid(row=1, column=0, padx=PAD, pady=(0, 10))

        self._e_email = self.make_entry(card, placeholder="Registered Email")

        self._e_email.grid(row=2, column=0, padx=PAD, pady=6, sticky="ew")

        self.make_button(
            card, "Send Reset Email",
            command=self._reset,
            color=C["accent"],
            height=BTN_HEIGHT,
        ).grid(row=3, column=0, padx=PAD, pady=(10, PAD), sticky="ew")

        self.make_back_button(self, "signin").grid(
            row=1, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def on_show(self) -> None:
        self._e_email.delete(0, "end")

    def _reset(self) -> None:
        email = self._e_email.get().strip()

        if not email or "@" not in email:
            self.controller.show_alert("Missing Email", "Please enter your registered email.")
            return

        try:
            # Send Firebase password reset email — user receives link in their Gmail
            fb_auth.send_password_reset_email(email)
            self.controller.show_alert(
                "Email Sent",
                f"A password reset link has been sent to:\n{email}\n\nCheck your inbox.",
            )
            self.controller.show_page("signin")
        except Exception as exc:
            self.controller.show_alert("Failed", f"Could not send reset email:\n{exc}")

