"""ui/keyboard.py — Floating on-screen keyboard overlay for the ABC Splash Kiosk.

Placed over the root window via place() geometry manager (does not disturb the
grid/pack layout of existing widgets).  A round floating toggle button sits in
the bottom-right corner and lets the cashier/operator show or hide the keyboard
at any time.  The keyboard also auto-shows whenever a bound CTkEntry receives
focus.

Key features
------------
- 5-row QWERTY layout with numbers, common symbols, @, backspace, Enter
- SHIFT  — one-shot: one keypress then auto-releases
- CAPS LOCK — persistent until toggled off; CAPS + SHIFT restores lowercase
- Large 17 pt bold labels for high-visibility on a 7-inch touchscreen
- Occupies exactly 30 % of the root window height, full width, flush to bottom
- Floating ⌨  toggle button (bottom-right); rises above keyboard when visible
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from typing import Optional

# ── Key layout ─────────────────────────────────────────────────────────────────
# Each cell is either:
#   • a plain str  — a static / control key whose label never changes
#   • a (normal, shifted) tuple — character key whose label flips with Shift/Caps
_ROWS: list[list] = [
    # Row 0 — numbers row
    [("1", "!"), ("2", "@"), ("3", "#"), ("4", "$"), ("5", "%"),
     ("6", "^"), ("7", "&"), ("8", "*"), ("9", "("), ("0", ")"), "⌫"],
    # Row 1 — QWERTY top row
    [("q", "Q"), ("w", "W"), ("e", "E"), ("r", "R"), ("t", "T"),
     ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), ("p", "P"), ("@", "@")],
    # Row 2 — ASDF home row
    [("a", "A"), ("s", "S"), ("d", "D"), ("f", "F"), ("g", "G"),
     ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), (";", ":"), "Enter"],
    # Row 3 — ZXCV bottom row
    [("z", "Z"), ("x", "X"), ("c", "C"), ("v", "V"), ("b", "B"),
     ("n", "N"), ("m", "M"), (",", "<"), (".", ">"), ("/", "?")],
    # Row 4 — control + symbol row
    ["CAPS", "SHIFT", "SPACE", ("-", "_"), ("'", '"'), ("!", "!"),
     ("?", "?"), ("#", "~")],
]

# ── Colours ────────────────────────────────────────────────────────────────────
_C = {
    "key_fg":        "#0d47a1",
    "key_hv":        "#1565c0",
    "action_fg":     "#b71c1c",   # backspace / enter
    "action_hv":     "#c62828",
    "mod_fg":        "#004d40",   # CAPS / SHIFT off
    "mod_hv":        "#00695c",
    "mod_on":        "#00bcd4",   # CAPS / SHIFT active (highlight)
    "space_fg":      "#37474f",
    "space_hv":      "#455a64",
    "kb_bg":         "#1a2744",
    "kb_border":     "#00a8ff",
    "toggle_fg":     "#0277bd",
    "toggle_hv":     "#01579b",
}

KB_HEIGHT_RATIO: float = 0.30   # keyboard = 30 % of root height
TOGGLE_SIZE:     int   = 60     # floating button side length (px)
TOGGLE_MARGIN:   int   = 12     # px from window edge
KEY_FONT_SIZE:   int   = 17     # pt — large for easy reading on touchscreen
KEY_CORNER:      int   = 6


class OnScreenKeyboard(ctk.CTkFrame):
    """Floating on-screen keyboard.  Instantiate once in MainApp after building
    pages; call ``bind_entries`` with all CTkEntry widgets that should trigger it.
    Call ``show_toggle`` / ``hide_toggle`` from ``show_page`` to restrict the
    keyboard and its button to authentication pages only.
    """

    def __init__(self, root: ctk.CTk) -> None:
        super().__init__(
            root,
            fg_color=_C["kb_bg"],
            corner_radius=0,
            border_color=_C["kb_border"],
            border_width=2,
        )
        self._root:    ctk.CTk              = root
        self._target:  Optional[ctk.CTkEntry] = None
        self._shift:   bool                 = False
        self._caps:    bool                 = False
        self._visible: bool                 = False

        # _btn_grid[row][col] = (CTkButton, key_definition)
        self._btn_grid: list[list[tuple[ctk.CTkButton, object]]] = []

        self._build_rows()

        # ── Floating toggle button (placed on root, not inside kb frame) ────
        self._toggle_btn = ctk.CTkButton(
            root,
            text="⌨",
            width=TOGGLE_SIZE,
            height=TOGGLE_SIZE,
            fg_color=_C["toggle_fg"],
            hover_color=_C["toggle_hv"],
            text_color="#ffffff",
            font=ctk.CTkFont("Segoe UI", 26, "bold"),
            corner_radius=TOGGLE_SIZE // 2,
            command=self.toggle,
        )
        # Not placed until show_toggle() is called

    # ── Build layout ───────────────────────────────────────────────────────────

    def _build_rows(self) -> None:
        """Create one row-frame per entry in _ROWS and populate buttons."""
        self.grid_columnconfigure(0, weight=1)
        for r_idx, row_def in enumerate(_ROWS):
            self.grid_rowconfigure(r_idx, weight=1)

            row_frame = ctk.CTkFrame(self, fg_color="transparent")
            row_frame.grid(row=r_idx, column=0, sticky="nsew", padx=4, pady=2)
            row_frame.grid_rowconfigure(0, weight=1)

            btn_row: list[tuple[ctk.CTkButton, object]] = []
            col = 0
            for key_def in row_def:
                label = self._resolve_label(key_def)
                btn   = self._make_key_button(row_frame, label, key_def)

                # Give SPACE 4× the column weight so it appears wide
                weight = 4 if (isinstance(key_def, str) and key_def == "SPACE") else 1
                row_frame.grid_columnconfigure(col, weight=weight)
                btn.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")

                btn_row.append((btn, key_def))
                col += 1

            self._btn_grid.append(btn_row)

    def _make_key_button(
        self,
        parent: ctk.CTkFrame,
        label: str,
        key_def,
    ) -> ctk.CTkButton:
        """Create one key button with appropriate colour coding."""
        key_id = key_def if isinstance(key_def, str) else key_def[0]

        if key_id in ("CAPS", "SHIFT"):
            fg, hv = _C["mod_fg"],    _C["mod_hv"]
        elif key_id in ("⌫", "Enter"):
            fg, hv = _C["action_fg"], _C["action_hv"]
        elif key_id == "SPACE":
            fg, hv = _C["space_fg"],  _C["space_hv"]
        else:
            fg, hv = _C["key_fg"],    _C["key_hv"]

        btn = ctk.CTkButton(
            parent,
            text=label,
            fg_color=fg,
            hover_color=hv,
            text_color="#ffffff",
            font=ctk.CTkFont("Segoe UI", KEY_FONT_SIZE, "bold"),
            corner_radius=KEY_CORNER,
            command=lambda kd=key_def: self._on_key_press(kd),
        )
        return btn

    # ── Label resolution ───────────────────────────────────────────────────────

    def _resolve_label(self, key_def, shift: bool = False, caps: bool = False) -> str:
        """Return the display/type label for a key given current modifier state."""
        if isinstance(key_def, str):
            return key_def           # Static keys: label stays the same

        normal, shifted = key_def
        if normal.isalpha():
            # CAPS XOR SHIFT — either one uppercases, both cancel out
            return shifted if (caps ^ shift) else normal
        else:
            # Number / symbol key: only SHIFT affects it
            return shifted if shift else normal

    # ── Key press handling ─────────────────────────────────────────────────────

    def _on_key_press(self, key_def) -> None:
        if isinstance(key_def, str):
            self._handle_control_key(key_def)
        else:
            char = self._resolve_label(key_def, self._shift, self._caps)
            self._insert_char(char)
            # SHIFT is one-shot: auto-release after a character is typed
            if self._shift:
                self._shift = False
                self._refresh_labels()

    def _handle_control_key(self, key: str) -> None:
        if key == "⌫":
            self._do_backspace()
        elif key == "SPACE":
            self._insert_char(" ")
        elif key == "Enter":
            pass   # No-op for single-line CTkEntry; keeps logic untouched
        elif key == "CAPS":
            self._caps = not self._caps
            self._refresh_labels()
        elif key == "SHIFT":
            self._shift = not self._shift
            self._refresh_labels()

    def _insert_char(self, char: str) -> None:
        entry = self._get_active_entry()
        if entry is None:
            return
        try:
            inner: tk.Entry = entry._entry
            inner.insert(tk.INSERT, char)
            inner.focus_set()   # Keep text cursor in entry after key tap
        except Exception:
            pass

    def _do_backspace(self) -> None:
        entry = self._get_active_entry()
        if entry is None:
            return
        try:
            inner: tk.Entry = entry._entry
            try:
                # Delete selected text if present
                sel_first = inner.index(tk.SEL_FIRST)
                sel_last  = inner.index(tk.SEL_LAST)
                inner.delete(sel_first, sel_last)
            except tk.TclError:
                # No selection — delete the character to the left of the cursor
                pos = inner.index(tk.INSERT)
                if pos > 0:
                    inner.delete(pos - 1, pos)
            inner.focus_set()
        except Exception:
            pass

    def _get_active_entry(self) -> Optional[ctk.CTkEntry]:
        """Walk the focused widget's parent chain looking for a CTkEntry.
        Falls back to the last-known target so key taps don't lose the entry
        (tapping a keyboard button shifts focus away from the text field).
        """
        try:
            focused = self._root.focus_get()
            widget  = focused
            while widget is not None:
                if isinstance(widget, ctk.CTkEntry):
                    self._target = widget   # update last-known target
                    return widget
                widget = getattr(widget, "master", None)
        except Exception:
            pass
        return self._target   # fallback

    # ── Shift / Caps label refresh ─────────────────────────────────────────────

    def _refresh_labels(self) -> None:
        """Update all button labels and modifier-key highlight colours."""
        for btn_row in self._btn_grid:
            for btn, key_def in btn_row:
                new_label = self._resolve_label(key_def, self._shift, self._caps)
                btn.configure(
                    text=new_label,
                    command=lambda kd=key_def: self._on_key_press(kd),
                )
                # Visually highlight active modifier keys
                if isinstance(key_def, str):
                    if key_def == "CAPS":
                        btn.configure(
                            fg_color=_C["mod_on"] if self._caps  else _C["mod_fg"],
                        )
                    elif key_def == "SHIFT":
                        btn.configure(
                            fg_color=_C["mod_on"] if self._shift else _C["mod_fg"],
                        )

    # ── Show / Hide / Toggle ───────────────────────────────────────────────────

    def show(self) -> None:
        if self._visible:
            return
        self._visible = True
        self._root.update_idletasks()
        w    = self._root.winfo_width()  or 1024
        h    = self._root.winfo_height() or 600
        kb_h = int(h * KB_HEIGHT_RATIO)
        # CustomTkinter forbids passing width/height to place(); set via configure first
        self.configure(width=w, height=kb_h)
        self.place(x=0, y=h - kb_h)
        self.lift()
        self._update_toggle_position()

    def hide(self) -> None:
        if not self._visible:
            return
        self._visible = False
        self.place_forget()
        self._update_toggle_position()

    def toggle(self) -> None:
        self.hide() if self._visible else self.show()

    # ── Toggle button visibility ──────────────────────────────────────────────

    def show_toggle(self) -> None:
        """Show the floating ⌨ button.  Call from show_page on auth pages."""
        self._update_toggle_position()
        self._toggle_btn.lift()

    def hide_toggle(self) -> None:
        """Hide the ⌨ button and also collapse the keyboard.  Call on other pages."""
        self._toggle_btn.place_forget()
        self.hide()

    def _update_toggle_position(self) -> None:
        """(Re)place the floating toggle button above the keyboard (if visible)
        or at the very bottom-right corner (if keyboard is hidden)."""
        self._root.update_idletasks()
        w    = self._root.winfo_width()  or 1024
        h    = self._root.winfo_height() or 600
        kb_h = int(h * KB_HEIGHT_RATIO)

        x = w - TOGGLE_SIZE - TOGGLE_MARGIN
        y = h - TOGGLE_SIZE - TOGGLE_MARGIN - (kb_h if self._visible else 0)

        # width/height are already set in the CTkButton constructor; place() only takes x/y
        self._toggle_btn.place(x=x, y=y)
        self._toggle_btn.lift()

    # ── Entry binding ──────────────────────────────────────────────────────────

    def bind_entries(self, entries: list) -> None:
        """Bind FocusIn on each CTkEntry (and its internal tk.Entry child) so
        the keyboard auto-shows and tracks the active field."""
        for entry in entries:
            entry.bind(
                "<FocusIn>",
                lambda _e, ent=entry: self._on_entry_focus(ent),
                add="+",
            )
            try:
                entry._entry.bind(
                    "<FocusIn>",
                    lambda _e, ent=entry: self._on_entry_focus(ent),
                    add="+",
                )
            except AttributeError:
                pass

    def _on_entry_focus(self, entry: ctk.CTkEntry) -> None:
        self._target = entry
        if not self._visible:
            self.show()
