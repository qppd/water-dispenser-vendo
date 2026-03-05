"""
ui/theme.py - Shared visual constants for the kiosk UI.

All pages import from here so a colour/font change needs editing
exactly one file.
"""

# ── Colour palette (matches HTML simulation) ──────────────────────────────────
C = {
    "aqua":       "#00a8ff",
    "accent":     "#2ecc71",
    "danger":     "#e74c3c",
    "dark_blue":  "#0277bd",
    "screen_bg":  "#e1f5fe",
    "sidebar_bg": "#01579b",
    "steel":      "#7f8c8d",
    "app_bg":     "#1a2744",
    "white":      "#ffffff",
    "text_dark":  "#1a2744",
    "warning":    "#f39c12",
    "btn_back":   "#90a4ae",
    "btn_other":  "#455a64",
    "cold":       "#039be5",
    "warm":       "#ffb300",
    "hot":        "#f4511e",
}

# ── Font sizes ────────────────────────────────────────────────────────────────
# Designed for a 1024×600 touchscreen: large = easy to tap.

F = {
    "title":   ("Segoe UI", 32, "bold"),
    "heading": ("Segoe UI", 20, "bold"),
    "sub":     ("Segoe UI", 15, "bold"),
    "body":    ("Segoe UI", 13),
    "small":   ("Segoe UI", 11),
    "btn":     ("Segoe UI", 14, "bold"),
    "btn_lg":  ("Segoe UI", 16, "bold"),
    "count":   ("Segoe UI", 72, "bold"),
}

# ── Button geometry ────────────────────────────────────────────────────────────
BTN_HEIGHT  = 55   # px — minimum comfortable touch target
BTN_WIDE    = 200  # px — default width for standard buttons
BTN_CORNER  = 10   # corner radius

# ── Layout ────────────────────────────────────────────────────────────────────
WIN_W       = 1024
WIN_H       = 600
SIDEBAR_W   = 200
CONTENT_W   = WIN_W - SIDEBAR_W   # 824 when sidebar shown
PAD         = 20                   # standard internal padding
