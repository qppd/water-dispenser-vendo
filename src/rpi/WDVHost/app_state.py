"""
app_state.py - Shared application state for the WDV kiosk.

The AppState singleton is passed to every UI page so they share the same
user session, transaction history, pending service selection, and hardware
event queue without any globals.
"""

import queue
from dataclasses import dataclass, field
from typing import List, Optional, Callable


# ── Pricing tables ──────────────────────────────────────────────────────────

PRICING_REGISTERED = [
    {"ml": 100,  "cost": 1},
    {"ml": 250,  "cost": 2},
    {"ml": 500,  "cost": 4},
    {"ml": 1000, "cost": 8},
]

PRICING_GUEST = [
    {"ml": 100,  "cost": 1},
    {"ml": 250,  "cost": 3},
    {"ml": 500,  "cost": 5},
    {"ml": 1000, "cost": 10},
]

# How many points a registered user gets per peso inserted
REGISTERED_RATES = {1: 1, 5: 6, 10: 13, 20: 25, 50: 60, 100: 115}

# Accepted cash denominations
CASH_VALUES = [1, 5, 10, 20, 50, 100]

# Relay open duration (ms) per ml — calibrate to real hardware
ML_TO_MS = {100: 1000, 250: 2500, 500: 5000, 1000: 10_000}

# Activation fee in pesos
ACTIVATION_FEE = 10

# Welcome bonus points awarded on registration
WELCOME_BONUS = 10


# ── User model ───────────────────────────────────────────────────────────────

@dataclass
class User:
    username: str = "Guest"
    email: str = "---"
    phone: str = "---"
    password: str = ""
    points: int = 0
    is_guest: bool = True

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "email":    self.email,
            "phone":    self.phone,
            "password": self.password,
            "points":   self.points,
            "is_guest": self.is_guest,
        }

    @staticmethod
    def from_dict(data: dict) -> "User":
        u = User()
        u.username = data.get("username", "Guest")
        u.email    = data.get("email",    "---")
        u.phone    = data.get("phone",    "---")
        u.password = data.get("password", "")
        u.points   = data.get("points",   0)
        u.is_guest = data.get("is_guest", True)
        return u


# ── Transaction record ───────────────────────────────────────────────────────

@dataclass
class Transaction:
    description: str          # e.g. "₱10 inserted"
    points_delta: int         # positive = gain, negative = spend
    timestamp: str = ""       # ISO string

    def to_dict(self) -> dict:
        return {
            "description":  self.description,
            "points_delta": self.points_delta,
            "timestamp":    self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "Transaction":
        t = Transaction(
            description=data.get("description", ""),
            points_delta=data.get("points_delta", 0),
            timestamp=data.get("timestamp", ""),
        )
        return t


# ── Service selection context ─────────────────────────────────────────────────

@dataclass
class ServiceSelection:
    service:     str = ""   # "Dispense" | "Fountain"
    temperature: str = ""   # "Cold" | "Warm" | "Hot"
    volume_ml:   int = 0
    cost_pts:    int = 0


# ── App-level state ───────────────────────────────────────────────────────────

class AppState:
    """
    Central mutable state container.  All UI pages hold a reference to the
    single AppState instance created in main.py.
    """

    def __init__(self) -> None:
        self.user: User = User()
        self.history: List[Transaction] = []
        self.selection: ServiceSelection = ServiceSelection()

        # Hardware event queue populated by SerialManager (background thread)
        # and drained by the main Tkinter thread via after().
        self.hw_event_queue: queue.Queue = queue.Queue()

        # Pending cash inserted during activation (pesos, not points)
        self._activation_cash: int = 0

        # Optional callbacks registered by the active page
        self._on_coin: Optional[Callable[[int], None]] = None
        self._on_bill: Optional[Callable[[int], None]] = None
        self._on_dispense_complete: Optional[Callable[[], None]] = None

    # ── User helpers ──────────────────────────────────────────────────────────

    def login(self, user: User) -> None:
        self.user = user
        self.user.is_guest = False
        self._activation_cash = 0

    def logout(self) -> None:
        self.user = User()          # reset to default Guest
        self.history = []
        self.selection = ServiceSelection()
        self._activation_cash = 0
        self.clear_callbacks()

    def login_guest(self) -> None:
        self.user = User(
            username="Guest User",
            email="Guest Access",
            phone="N/A",
            points=0,
            password="",
            is_guest=True,
        )
        self.history = []
        self._activation_cash = 0

    # ── Points helpers ────────────────────────────────────────────────────────

    def add_cash(self, peso_value: int, is_activation: bool = False) -> int:
        """Convert pesos to points and credit the current user.
        Returns the number of points added.
        """
        if is_activation:
            self._activation_cash += peso_value
            pts = peso_value  # 1:1 for tracking during registration flow
        elif self.user.is_guest:
            pts = peso_value  # guests: 1 peso = 1 point
        else:
            pts = REGISTERED_RATES.get(peso_value, peso_value)

        self.user.points += pts
        self.add_transaction(f"₱{peso_value} inserted", pts)
        return pts

    def activation_cash_inserted(self) -> int:
        """Total pesos inserted since the registration flow started."""
        return self._activation_cash

    def reset_activation_cash(self) -> None:
        self._activation_cash = 0

    def deduct_points(self, pts: int, description: str) -> bool:
        if self.user.points < pts:
            return False
        self.user.points -= pts
        self.add_transaction(description, -pts)
        return True

    # ── History helpers ───────────────────────────────────────────────────────

    def add_transaction(self, description: str, points_delta: int) -> None:
        from datetime import datetime
        t = Transaction(
            description=description,
            points_delta=points_delta,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.history.insert(0, t)

    # ── Callback registration ──────────────────────────────────────────────────

    def register_coin_callback(self, cb: Optional[Callable[[int], None]]) -> None:
        self._on_coin = cb

    def register_bill_callback(self, cb: Optional[Callable[[int], None]]) -> None:
        self._on_bill = cb

    def register_dispense_complete_callback(
        self, cb: Optional[Callable[[], None]]
    ) -> None:
        self._on_dispense_complete = cb

    def clear_callbacks(self) -> None:
        self._on_coin = None
        self._on_bill = None
        self._on_dispense_complete = None

    def dispatch_coin(self, value: int) -> None:
        if self._on_coin:
            self._on_coin(value)

    def dispatch_bill(self, value: int) -> None:
        if self._on_bill:
            self._on_bill(value)

    def dispatch_dispense_complete(self) -> None:
        if self._on_dispense_complete:
            self._on_dispense_complete()
