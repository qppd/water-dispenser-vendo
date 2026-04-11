import queue
import threading
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
    # Firebase UID — set on login; not stored in RTDB (stripped by storage.py)
    uid: str = ""

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "email":    self.email,
            "phone":    self.phone,
            "password": self.password,
            "points":   self.points,
            "is_guest": self.is_guest,
            "uid":      self.uid,
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
        u.uid      = data.get("uid",      "")
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

        # Temperature readings from ESPWDV (updated every ~5 s by SecondESPSerial)
        # Values are float °C, or None until the first reading arrives.
        self.temperatures: dict = {"HOT": None, "WARM": None, "COLD": None}

        # Optional callbacks registered by the active page
        self._on_coin: Optional[Callable[[int], None]] = None
        self._on_bill: Optional[Callable[[int], None]] = None
        self._on_dispense_complete: Optional[Callable[[], None]] = None
        self._on_qr_scanned: Optional[Callable[[str], None]] = None
        self._on_temperature_update: Optional[Callable[[], None]] = None

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
        self._sync_points_async()
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
        self._sync_points_async()
        return True

    def _sync_points_async(self) -> None:
        """Push the current user's points to Firebase RTDB in a background thread.

        No-op for guest sessions or if uid is unknown.
        Errors are logged but never raised — the kiosk must not crash on sync issues.
        """
        if self.user.is_guest or not self.user.uid:
            return
        uid    = self.user.uid
        points = self.user.points

        def _do() -> None:
            try:
                from firebase_config import admin_db
                admin_db.reference(f"users/{uid}/points").set(points)
            except Exception as exc:
                print(f"[AppState] Firebase sync error: {exc}")

        threading.Thread(target=_do, daemon=True).start()

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

    def register_qr_callback(
        self, cb: Optional[Callable[[str], None]]
    ) -> None:
        self._on_qr_scanned = cb

    def clear_callbacks(self) -> None:
        self._on_coin = None
        self._on_bill = None
        self._on_dispense_complete = None
        self._on_qr_scanned = None
        self._on_temperature_update = None

    def dispatch_coin(self, value: int) -> None:
        if self._on_coin:
            self._on_coin(value)

    def dispatch_bill(self, value: int) -> None:
        if self._on_bill:
            self._on_bill(value)

    def dispatch_dispense_complete(self) -> None:
        if self._on_dispense_complete:
            self._on_dispense_complete()

    def dispatch_qr_scanned(self, data: str) -> None:
        if self._on_qr_scanned:
            self._on_qr_scanned(data)

    # ── Temperature helpers ───────────────────────────────────────────────────

    def update_temperature(self, sensor: str, value: float) -> None:
        """Store a new temperature reading and fire the update callback."""
        if sensor in self.temperatures:
            self.temperatures[sensor] = value
            if self._on_temperature_update:
                self._on_temperature_update()

    def register_temperature_callback(
        self, cb: Optional[Callable[[], None]]
    ) -> None:
        self._on_temperature_update = cb
