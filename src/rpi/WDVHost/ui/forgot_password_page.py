import customtkinter as ctk
from ui.base_page import BasePage
from ui.theme import C, F, BTN_HEIGHT, PAD
import storage


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
            text="Enter your registered phone number to verify your identity.",
            font=ctk.CTkFont(*F["small"]),
            text_color=C["steel"],
            wraplength=280,
        ).grid(row=1, column=0, padx=PAD, pady=(0, 10))

        self._e_phone = self.make_entry(card, placeholder="Registered Phone Number")
        self._e_pass  = self.make_entry(card, placeholder="New Password", show="●")

        self._e_phone.grid(row=2, column=0, padx=PAD, pady=6, sticky="ew")
        self._e_pass.grid( row=3, column=0, padx=PAD, pady=6, sticky="ew")

        self.make_button(
            card, "Update Password",
            command=self._reset,
            color=C["accent"],
            height=BTN_HEIGHT,
        ).grid(row=4, column=0, padx=PAD, pady=(10, PAD), sticky="ew")

        self.make_back_button(self, "signin").grid(
            row=1, column=0, padx=PAD, pady=(0, PAD), sticky="w"
        )

    def on_show(self) -> None:
        self._e_phone.delete(0, "end")
        self._e_pass.delete(0, "end")

    def _reset(self) -> None:
        phone    = self._e_phone.get().strip()
        new_pass = self._e_pass.get()

        data = storage.find_user_by_phone(phone)
        if data:
            data["password"] = new_pass
            storage.save_user(data)
            self.controller.show_alert("Password Updated", "Your password has been updated.")
            self.controller.show_page("signin")
        else:
            self.controller.show_alert("Not Found", "No account with that phone number.")
