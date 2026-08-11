"""
================================================================================
LOW LEVEL DESIGN (LLD) — SDE INTERVIEW QUESTION BANK (PYTHON)
================================================================================
This single document bundles 8 of the most frequently asked LLD questions in
current (2025-2026) SDE / SDE-2 interviews at product companies.

IMPORTANT — HOW THIS FILE IS ORGANIZED:
Each problem below is written as an INDEPENDENT, SELF-CONTAINED unit — as if it
were its own separate .py file. That is why:
  1. Imports are NOT hoisted/shared at the top of this document. Each section
     re-imports exactly what IT needs (e.g. `from enum import Enum` appears
     8 times). This mirrors how you'd actually submit/organize these in an
     interview or a real repo (one file per system), and avoids the classic
     mistake of silently depending on another problem's imports/classes —
     which would break the moment you copy just ONE section out on its own.
  2. Class/Enum names are deliberately kept local to each section (no shared
     "Base" classes across problems) so you can copy-paste any single section
     into its own file and run it with zero missing-symbol errors.
  3. Every section has a docstring at the top explaining:
        - The core requirements being modeled
        - WHY specific design patterns were chosen (trade-offs, not just names)
        - Where interviewers commonly probe follow-up questions

Design patterns you'll see recur across problems (this is intentional — these
are the patterns interviewers are actually testing for):
  - Singleton      : exactly one coordinating instance (ParkingLot, BookingSystem)
  - Factory        : centralize object creation, hide concrete subclass choice
  - Strategy       : swap an algorithm/policy at runtime (pricing, splitting, rate-limiting)
  - Observer       : one-to-many change notification (seat locks, elevator arrival)
  - State          : object behavior changes with internal state (elevator, order)
  - Decorator      : attach behavior to an object without touching its class (notifications)
  - Composite/SRP  : keep each class doing ONE job so the system stays extensible
================================================================================
"""


# ==============================================================================
# FILE 1/8: parking_lot.py
# ==============================================================================
"""
PROBLEM: Design a Parking Lot System.

REQUIREMENTS MODELED:
 - Multiple floors, each with multiple spots of different sizes (bike/car/truck).
 - A vehicle should be parked in the smallest spot that fits it (no wasted big
   spots on small vehicles).
 - Compute fee on exit based on duration.

WHY THESE PATTERNS:
 - SINGLETON (ParkingLot): There is physically only ONE parking lot coordinating
   all floors/spots — allowing two independent instances risks double-allocating
   the same spot. Singleton enforces "one source of truth" for spot inventory.
 - FACTORY (VehicleFactory): Vehicle creation logic (deciding subclass from a
   type string) is centralized so callers never need `if type == "car": Car()`
   scattered everywhere — new vehicle types only require one factory edit.
 - STRATEGY (FeeStrategy): Fee calculation rules change often (hourly vs flat
   vs weekend pricing). Making it a swappable strategy means we change pricing
   WITHOUT touching ParkingLot/Spot logic — Open/Closed Principle in action.

COMMON FOLLOW-UPS:
 - What if two threads try to park in the same spot? (discuss locking on Spot)
 - How to support reservations ahead of time?
 - How to support hourly vs. subscription-based parking?
"""
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import threading


class VehicleType(Enum):
    BIKE = 1
    CAR = 2
    TRUCK = 3


class Vehicle:
    def __init__(self, plate_number: str, vehicle_type: VehicleType):
        self.plate_number = plate_number
        self.vehicle_type = vehicle_type


class VehicleFactory:
    """FACTORY PATTERN: single place to create Vehicle objects from raw input."""
    @staticmethod
    def create_vehicle(plate_number: str, type_str: str) -> Vehicle:
        mapping = {"bike": VehicleType.BIKE, "car": VehicleType.CAR, "truck": VehicleType.TRUCK}
        if type_str not in mapping:
            raise ValueError(f"Unknown vehicle type: {type_str}")
        return Vehicle(plate_number, mapping[type_str])


class ParkingSpot:
    def __init__(self, spot_id: str, spot_type: VehicleType):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.vehicle: Vehicle | None = None
        self.lock = threading.Lock()  # protects against double-booking from concurrent requests

    def is_free(self) -> bool:
        return self.vehicle is None

    def can_fit(self, vehicle: Vehicle) -> bool:
        # A spot can fit a vehicle only if it's the same size class or bigger
        return vehicle.vehicle_type.value <= self.spot_type.value

    def park(self, vehicle: Vehicle) -> bool:
        with self.lock:
            if not self.is_free():
                return False
            self.vehicle = vehicle
            return True

    def vacate(self):
        with self.lock:
            self.vehicle = None


class Floor:
    def __init__(self, floor_number: int, spots: list[ParkingSpot]):
        self.floor_number = floor_number
        self.spots = spots

    def find_spot(self, vehicle: Vehicle) -> ParkingSpot | None:
        # pick the SMALLEST spot that fits, to avoid wasting large spots
        candidates = sorted(
            (s for s in self.spots if s.is_free() and s.can_fit(vehicle)),
            key=lambda s: s.spot_type.value,
        )
        return candidates[0] if candidates else None


class FeeStrategy(ABC):
    """STRATEGY PATTERN: pluggable pricing algorithm."""
    @abstractmethod
    def calculate(self, entry_time: datetime, exit_time: datetime) -> float:
        ...


class HourlyFeeStrategy(FeeStrategy):
    def __init__(self, rate_per_hour: float = 20.0):
        self.rate_per_hour = rate_per_hour

    def calculate(self, entry_time: datetime, exit_time: datetime) -> float:
        hours = max(1, (exit_time - entry_time).seconds // 3600 + 1)
        return hours * self.rate_per_hour


class Ticket:
    def __init__(self, ticket_id: str, vehicle: Vehicle, spot: ParkingSpot, entry_time: datetime):
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        self.spot = spot
        self.entry_time = entry_time
        self.exit_time: datetime | None = None


class ParkingLot:
    """SINGLETON PATTERN: only one lot manages the shared spot inventory."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, floors: list[Floor] = None, fee_strategy: FeeStrategy = None):
        if self._initialized:
            return
        self.floors = floors or []
        self.fee_strategy = fee_strategy or HourlyFeeStrategy()
        self.active_tickets: dict[str, Ticket] = {}
        self._ticket_seq = 0
        self._initialized = True

    def park_vehicle(self, vehicle: Vehicle) -> Ticket | None:
        for floor in self.floors:
            spot = floor.find_spot(vehicle)
            if spot and spot.park(vehicle):
                self._ticket_seq += 1
                ticket = Ticket(f"T{self._ticket_seq}", vehicle, spot, datetime.now())
                self.active_tickets[ticket.ticket_id] = ticket
                return ticket
        return None  # lot full

    def unpark_vehicle(self, ticket_id: str) -> float:
        ticket = self.active_tickets.pop(ticket_id)
        ticket.exit_time = datetime.now()
        ticket.spot.vacate()
        return self.fee_strategy.calculate(ticket.entry_time, ticket.exit_time)


# ==============================================================================
# FILE 2/8: elevator_system.py
# ==============================================================================
"""
PROBLEM: Design an Elevator System (single or multi-car).

REQUIREMENTS MODELED:
 - Elevator moves up/down, opens/closes doors, services floor requests.
 - A central controller assigns the best elevator to a hall call.

WHY THESE PATTERNS:
 - STATE PATTERN (ElevatorState subclasses): An elevator's valid actions depend
   entirely on its current state (you can't "open doors" while MOVING). Instead
   of a tangle of if/elif on a status flag, each state encapsulates its own
   legal transitions — adding a new state (e.g. MAINTENANCE) doesn't touch
   existing state classes.
 - OBSERVER PATTERN (FloorDisplay subscribes to Elevator): Floor displays and
   direction indicators need to react whenever the elevator's floor/state
   changes, without the Elevator class knowing anything about UI/display code.
   This decouples core elevator logic from anything that reacts to it.

COMMON FOLLOW-UPS:
 - How does the Controller pick which elevator to dispatch (nearest-car algorithm)?
 - How do you avoid starvation (a floor never gets serviced)?
 - How to scale to N elevators sharing hall requests?
"""
from abc import ABC, abstractmethod
from enum import Enum


class Direction(Enum):
    UP = 1
    DOWN = 2
    IDLE = 3


class ElevatorState(ABC):
    """STATE PATTERN base: encapsulates behavior + legal transitions per state."""
    @abstractmethod
    def move(self, elevator: "Elevator"):
        ...

    @abstractmethod
    def open_doors(self, elevator: "Elevator"):
        ...


class IdleState(ElevatorState):
    def move(self, elevator: "Elevator"):
        elevator.state = MovingState()
        print(f"Elevator {elevator.id}: leaving idle, now moving")

    def open_doors(self, elevator: "Elevator"):
        print(f"Elevator {elevator.id}: doors opening (was idle)")


class MovingState(ElevatorState):
    def move(self, elevator: "Elevator"):
        print(f"Elevator {elevator.id}: already moving, continuing")

    def open_doors(self, elevator: "Elevator"):
        print(f"Elevator {elevator.id}: cannot open doors while moving!")


class DoorsOpenState(ElevatorState):
    def move(self, elevator: "Elevator"):
        print(f"Elevator {elevator.id}: closing doors before moving")
        elevator.state = MovingState()

    def open_doors(self, elevator: "Elevator"):
        print(f"Elevator {elevator.id}: doors already open")


class FloorDisplay:
    """OBSERVER: reacts to elevator floor/state changes without elevator knowing details."""
    def update(self, elevator_id: int, floor: int, direction: Direction):
        print(f"[Display] Elevator {elevator_id} now at floor {floor}, direction {direction.name}")


class Elevator:
    def __init__(self, elevator_id: int, current_floor: int = 0):
        self.id = elevator_id
        self.current_floor = current_floor
        self.direction = Direction.IDLE
        self.state: ElevatorState = IdleState()
        self.requests: list[int] = []
        self.observers: list[FloorDisplay] = []

    def subscribe(self, observer: FloorDisplay):
        self.observers.append(observer)

    def _notify(self):
        for obs in self.observers:
            obs.update(self.id, self.current_floor, self.direction)

    def request_floor(self, floor: int):
        self.requests.append(floor)
        self.requests.sort(key=lambda f: abs(f - self.current_floor))

    def step(self):
        """Advance one floor towards the next requested floor."""
        if not self.requests:
            self.state = IdleState()
            return
        self.state.move(self)
        target = self.requests[0]
        if target > self.current_floor:
            self.current_floor += 1
            self.direction = Direction.UP
        elif target < self.current_floor:
            self.current_floor -= 1
            self.direction = Direction.DOWN
        if self.current_floor == target:
            self.requests.pop(0)
            self.state = DoorsOpenState()
            self.state.open_doors(self)
            self.direction = Direction.IDLE
        self._notify()


class ElevatorController:
    """Assigns the nearest idle-ish elevator to a hall call (simplified dispatch algorithm)."""
    def __init__(self, elevators: list[Elevator]):
        self.elevators = elevators

    def dispatch(self, floor: int):
        best = min(self.elevators, key=lambda e: abs(e.current_floor - floor))
        best.request_floor(floor)
        return best


# ==============================================================================
# FILE 3/8: lru_cache.py
# ==============================================================================
"""
PROBLEM: Design an LRU (Least Recently Used) Cache with O(1) get/put.

REQUIREMENTS MODELED:
 - get(key) -> value in O(1), marks key as most-recently-used.
 - put(key, value) in O(1), evicts least-recently-used key when capacity exceeded.

WHY THIS DESIGN (no heavyweight GoF pattern needed here — and that's a valid
interview answer!):
 - DOUBLY LINKED LIST + HASH MAP is the textbook O(1)/O(1) structure: the hash
   map gives O(1) node lookup, the linked list gives O(1) reordering
   (move-to-front) and O(1) eviction (drop from tail) — an array-based
   structure would force O(n) shifting.
 - Interviewers often SPECIFICALLY want you to justify NOT reaching for a
   "cute" pattern here — recognizing when a data-structure choice is the real
   design decision (vs. a class-hierarchy pattern) is itself a signal.

COMMON FOLLOW-UPS:
 - Thread-safety (add a lock around critical sections).
 - LFU variant (needs frequency buckets, not just recency).
 - TTL-based expiry on top of LRU.
"""


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev: "_Node | None" = None
        self.next: "_Node | None" = None


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.map: dict[int, _Node] = {}
        # sentinel head/tail avoid None-checks on every insert/remove
        self.head = _Node()
        self.tail = _Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: _Node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_front(self, node: _Node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node)
        self._add_to_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        if key in self.map:
            self._remove(self.map[key])
        node = _Node(key, value)
        self.map[key] = node
        self._add_to_front(node)
        if len(self.map) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]


# ==============================================================================
# FILE 4/8: rate_limiter.py
# ==============================================================================
"""
PROBLEM: Design a Rate Limiter (e.g. API gateway throttling per user/IP).

REQUIREMENTS MODELED:
 - Allow N requests per time window per client key.
 - Support swapping the underlying algorithm (token bucket, sliding window, etc).

WHY THIS PATTERN:
 - STRATEGY PATTERN (RateLimiterAlgorithm): Rate limiting algorithms
   (token bucket, leaky bucket, fixed window, sliding log) have wildly
   different memory/accuracy trade-offs, and interviewers routinely ask
   "now swap in a different algorithm." Strategy makes that a one-line
   change at the call site instead of a rewrite.

COMMON FOLLOW-UPS:
 - Distributed rate limiting (Redis + Lua script for atomicity).
 - Per-endpoint vs. per-user vs. global limits (composable limiters).
 - Burst handling (token bucket capacity vs. refill rate).
"""
from abc import ABC, abstractmethod
import time


class RateLimiterAlgorithm(ABC):
    """STRATEGY PATTERN base for pluggable throttling algorithms."""
    @abstractmethod
    def allow_request(self, client_id: str) -> bool:
        ...


class TokenBucketLimiter(RateLimiterAlgorithm):
    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.buckets: dict[str, list[float]] = {}  # client_id -> [tokens, last_refill_ts]

    def allow_request(self, client_id: str) -> bool:
        now = time.time()
        tokens, last_ts = self.buckets.get(client_id, [self.capacity, now])
        elapsed = now - last_ts
        tokens = min(self.capacity, tokens + elapsed * self.refill_rate)
        if tokens >= 1:
            tokens -= 1
            self.buckets[client_id] = [tokens, now]
            return True
        self.buckets[client_id] = [tokens, now]
        return False


class FixedWindowLimiter(RateLimiterAlgorithm):
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.windows: dict[str, list] = {}  # client_id -> [window_start, count]

    def allow_request(self, client_id: str) -> bool:
        now = time.time()
        window_start, count = self.windows.get(client_id, [now, 0])
        if now - window_start >= self.window_seconds:
            window_start, count = now, 0
        if count < self.max_requests:
            self.windows[client_id] = [window_start, count + 1]
            return True
        self.windows[client_id] = [window_start, count]
        return False


class RateLimiter:
    """Context that delegates to whichever algorithm strategy is configured."""
    def __init__(self, algorithm: RateLimiterAlgorithm):
        self.algorithm = algorithm

    def is_allowed(self, client_id: str) -> bool:
        return self.algorithm.allow_request(client_id)

    def set_algorithm(self, algorithm: RateLimiterAlgorithm):
        # swap strategy at runtime — no changes needed elsewhere
        self.algorithm = algorithm


# ==============================================================================
# FILE 5/8: splitwise.py
# ==============================================================================
"""
PROBLEM: Design an Expense-Sharing System (Splitwise-like).

REQUIREMENTS MODELED:
 - A group of users can add an expense that's split EQUALLY, by EXACT amounts,
   or by PERCENTAGE.
 - Track net balances between users ("who owes whom how much").

WHY THIS PATTERN:
 - STRATEGY PATTERN (SplitStrategy): The split RULE is the one part of this
   system that changes per-expense. Encoding it as interchangeable strategy
   objects means Expense/Group code never needs to know HOW a split is
   computed — and adding a new split type (e.g. "by shares") is a new class,
   not a new branch in existing code (Open/Closed Principle).

COMMON FOLLOW-UPS:
 - Simplify debts across a group (min-cash-flow / graph settlement algorithm).
 - Handle multi-currency expenses.
 - Support partial settlements/payments.
"""
from abc import ABC, abstractmethod
from collections import defaultdict


class User:
    def __init__(self, user_id: str, name: str):
        self.user_id = user_id
        self.name = name


class SplitStrategy(ABC):
    """STRATEGY PATTERN base: defines HOW an expense amount is divided."""
    @abstractmethod
    def compute_shares(self, amount: float, participants: list[User], **kwargs) -> dict[str, float]:
        ...


class EqualSplitStrategy(SplitStrategy):
    def compute_shares(self, amount: float, participants: list[User], **kwargs) -> dict[str, float]:
        share = round(amount / len(participants), 2)
        return {p.user_id: share for p in participants}


class ExactSplitStrategy(SplitStrategy):
    def compute_shares(self, amount: float, participants: list[User], exact_amounts: dict[str, float] = None, **kwargs) -> dict[str, float]:
        if round(sum(exact_amounts.values()), 2) != round(amount, 2):
            raise ValueError("Exact split amounts must sum to the total expense amount")
        return exact_amounts


class PercentSplitStrategy(SplitStrategy):
    def compute_shares(self, amount: float, participants: list[User], percentages: dict[str, float] = None, **kwargs) -> dict[str, float]:
        if round(sum(percentages.values()), 2) != 100.0:
            raise ValueError("Percentages must sum to 100")
        return {uid: round(amount * pct / 100, 2) for uid, pct in percentages.items()}


class Expense:
    def __init__(self, paid_by: User, amount: float, participants: list[User], strategy: SplitStrategy, **strategy_kwargs):
        self.paid_by = paid_by
        self.amount = amount
        self.shares = strategy.compute_shares(amount, participants, **strategy_kwargs)


class Group:
    def __init__(self, name: str):
        self.name = name
        self.expenses: list[Expense] = []
        # balances[A][B] = amount B owes A
        self.balances: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def add_expense(self, expense: Expense):
        self.expenses.append(expense)
        for user_id, share in expense.shares.items():
            if user_id != expense.paid_by.user_id:
                self.balances[expense.paid_by.user_id][user_id] += share

    def get_balance_summary(self) -> list[str]:
        lines = []
        for creditor, debtors in self.balances.items():
            for debtor, amt in debtors.items():
                if amt > 0:
                    lines.append(f"{debtor} owes {creditor}: {amt:.2f}")
        return lines


# ==============================================================================
# FILE 6/8: tic_tac_toe.py
# ==============================================================================
"""
PROBLEM: Design a Tic-Tac-Toe Game (2-player, NxN board).

REQUIREMENTS MODELED:
 - N x N board, two players alternate turns, detect win/draw.

WHY THIS PATTERN:
 - FACTORY-ish PLAYER ABSTRACTION + SRP: Board only knows about placing marks
   and checking win conditions; Game only knows about turn order; Player only
   knows its own symbol. Keeping these three responsibilities in three
   separate classes (Single Responsibility Principle) is exactly what
   interviewers are probing for in "simple" LLD questions like this one —
   they want to see clean separation, not clever patterns.
 - STRATEGY-READY WinChecker: win-checking is isolated in its own method so a
   follow-up ("what if it's NxN not 3x3?" or "what about diagonal-only wins?")
   is a local change, not a rewrite.

COMMON FOLLOW-UPS:
 - Generalize board size N and win-length K (Gomoku-style).
 - Add an AI player (Strategy pattern for move-selection algorithm).
 - Undo last move (Command / Memento pattern).
"""
from enum import Enum


class Symbol(Enum):
    X = "X"
    O = "O"
    EMPTY = "_"


class Player:
    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol


class Board:
    def __init__(self, size: int = 3):
        self.size = size
        self.grid = [[Symbol.EMPTY for _ in range(size)] for _ in range(size)]

    def place(self, row: int, col: int, symbol: Symbol) -> bool:
        if self.grid[row][col] != Symbol.EMPTY:
            return False
        self.grid[row][col] = symbol
        return True

    def is_full(self) -> bool:
        return all(cell != Symbol.EMPTY for row in self.grid for cell in row)

    def check_winner(self, symbol: Symbol) -> bool:
        n = self.size
        g = self.grid
        for i in range(n):
            if all(g[i][j] == symbol for j in range(n)):  # row
                return True
            if all(g[j][i] == symbol for j in range(n)):  # column
                return True
        if all(g[i][i] == symbol for i in range(n)):       # main diagonal
            return True
        if all(g[i][n - 1 - i] == symbol for i in range(n)):  # anti-diagonal
            return True
        return False

    def display(self):
        for row in self.grid:
            print(" ".join(cell.value for cell in row))


class TicTacToeGame:
    def __init__(self, player1: Player, player2: Player, size: int = 3):
        self.board = Board(size)
        self.players = [player1, player2]
        self.turn = 0

    def play_move(self, row: int, col: int) -> str:
        current = self.players[self.turn % 2]
        if not self.board.place(row, col, current.symbol):
            return "Invalid move, cell occupied"
        if self.board.check_winner(current.symbol):
            return f"{current.name} wins!"
        if self.board.is_full():
            return "Game is a draw"
        self.turn += 1
        return "Move accepted"


# ==============================================================================
# FILE 7/8: movie_ticket_booking.py
# ==============================================================================
"""
PROBLEM: Design a Movie Ticket Booking System (BookMyShow-style).

REQUIREMENTS MODELED:
 - Theatres have shows; shows have a seat map; users lock a seat then confirm
   payment before it's permanently booked.
 - Multiple users must never be able to double-book the same seat.

WHY THESE PATTERNS:
 - SINGLETON (BookingService): a single service instance must own the seat
   locking logic so two concurrent booking flows can't race past each other
   and both "successfully" lock the same seat.
 - OBSERVER (SeatAvailabilityObserver): other subsystems (search-results cache,
   notification service) need to know the instant a seat's status changes,
   without BookingService importing/knowing about them directly.
 - a TIME-BASED LOCK (expiring hold) models the real "seat held for 5 minutes
   during checkout" UX — a very common interviewer follow-up.

COMMON FOLLOW-UPS:
 - What happens if payment fails after lock? (release lock / TTL expiry)
 - Concurrency: use per-seat locks, not a global lock, for throughput.
 - How would you support waitlists?
"""
from enum import Enum
from datetime import datetime, timedelta
import threading


class SeatStatus(Enum):
    AVAILABLE = 1
    LOCKED = 2
    BOOKED = 3


class Seat:
    def __init__(self, seat_id: str):
        self.seat_id = seat_id
        self.status = SeatStatus.AVAILABLE
        self.locked_until: datetime | None = None
        self.lock = threading.Lock()  # per-seat lock avoids a global bottleneck

    def try_lock(self, hold_minutes: int = 5) -> bool:
        with self.lock:
            if self.status == SeatStatus.BOOKED:
                return False
            if self.status == SeatStatus.LOCKED and self.locked_until > datetime.now():
                return False
            self.status = SeatStatus.LOCKED
            self.locked_until = datetime.now() + timedelta(minutes=hold_minutes)
            return True

    def confirm_booking(self):
        with self.lock:
            self.status = SeatStatus.BOOKED

    def release(self):
        with self.lock:
            self.status = SeatStatus.AVAILABLE
            self.locked_until = None


class SeatAvailabilityObserver:
    """OBSERVER: notified whenever a seat's status changes."""
    def on_seat_status_changed(self, show_id: str, seat_id: str, status: SeatStatus):
        print(f"[Notify] Show {show_id} seat {seat_id} -> {status.name}")


class Show:
    def __init__(self, show_id: str, movie_name: str, seats: list[Seat]):
        self.show_id = show_id
        self.movie_name = movie_name
        self.seats = {s.seat_id: s for s in seats}


class BookingService:
    """SINGLETON: single authority over seat locking to prevent double-booking."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.observers = []
        return cls._instance

    def subscribe(self, observer: SeatAvailabilityObserver):
        self.observers.append(observer)

    def _notify(self, show_id: str, seat_id: str, status: SeatStatus):
        for obs in self.observers:
            obs.on_seat_status_changed(show_id, seat_id, status)

    def lock_seat(self, show: Show, seat_id: str) -> bool:
        seat = show.seats[seat_id]
        success = seat.try_lock()
        if success:
            self._notify(show.show_id, seat_id, SeatStatus.LOCKED)
        return success

    def confirm_payment(self, show: Show, seat_id: str) -> bool:
        seat = show.seats[seat_id]
        if seat.status != SeatStatus.LOCKED:
            return False
        seat.confirm_booking()
        self._notify(show.show_id, seat_id, SeatStatus.BOOKED)
        return True


# ==============================================================================
# FILE 8/8: notification_system.py
# ==============================================================================
"""
PROBLEM: Design a Notification System (email / SMS / push, with add-ons).

REQUIREMENTS MODELED:
 - Send a notification through one or more channels (email, SMS, push).
 - Optionally attach cross-cutting extras (logging, retry) without editing
   the core notifier classes.

WHY THESE PATTERNS:
 - OBSERVER (NotificationDispatcher notifies all subscribed channels): a
   single event ("order shipped") often must fan out to several channels at
   once — Observer is the direct fit for one-event-to-many-handlers.
 - FACTORY (NotifierFactory): centralizes creation of the right channel-sender
   from a config string, so the dispatcher never hardcodes channel classes.
 - DECORATOR (LoggingNotifierDecorator / RetryNotifierDecorator): logging and
   retry-on-failure are cross-cutting concerns that apply to ANY channel.
   Wrapping a base Notifier in decorators adds behavior without subclassing
   every channel type separately (avoids a combinatorial class explosion like
   EmailNotifierWithLoggingAndRetry, SMSNotifierWithLoggingAndRetry, ...).

COMMON FOLLOW-UPS:
 - Per-user channel preferences / opt-outs.
 - Rate limiting notifications (reuse the RateLimiter strategy from problem 4!).
 - Template rendering per channel (Strategy for message formatting).
"""
from abc import ABC, abstractmethod


class Notifier(ABC):
    """Common interface every channel and decorator conforms to."""
    @abstractmethod
    def send(self, message: str) -> bool:
        ...


class EmailNotifier(Notifier):
    def send(self, message: str) -> bool:
        print(f"[Email] {message}")
        return True


class SMSNotifier(Notifier):
    def send(self, message: str) -> bool:
        print(f"[SMS] {message}")
        return True


class PushNotifier(Notifier):
    def send(self, message: str) -> bool:
        print(f"[Push] {message}")
        return True


class NotifierFactory:
    """FACTORY PATTERN: hides concrete channel classes from the dispatcher."""
    @staticmethod
    def create(channel: str) -> Notifier:
        registry = {"email": EmailNotifier, "sms": SMSNotifier, "push": PushNotifier}
        if channel not in registry:
            raise ValueError(f"Unsupported channel: {channel}")
        return registry[channel]()


class NotifierDecorator(Notifier):
    """DECORATOR PATTERN base: wraps a Notifier to add behavior transparently."""
    def __init__(self, wrapped: Notifier):
        self._wrapped = wrapped

    @abstractmethod
    def send(self, message: str) -> bool:
        ...


class LoggingNotifierDecorator(NotifierDecorator):
    def send(self, message: str) -> bool:
        print(f"[Log] About to send: {message}")
        result = self._wrapped.send(message)
        print(f"[Log] Send result: {result}")
        return result


class RetryNotifierDecorator(NotifierDecorator):
    def __init__(self, wrapped: Notifier, max_retries: int = 3):
        super().__init__(wrapped)
        self.max_retries = max_retries

    def send(self, message: str) -> bool:
        for attempt in range(1, self.max_retries + 1):
            if self._wrapped.send(message):
                return True
            print(f"[Retry] attempt {attempt} failed, retrying...")
        return False


class NotificationDispatcher:
    """OBSERVER-style fan-out: one event, many subscribed channel notifiers."""
    def __init__(self):
        self.channels: list[Notifier] = []

    def subscribe(self, notifier: Notifier):
        self.channels.append(notifier)

    def dispatch(self, message: str):
        for channel in self.channels:
            channel.send(message)


# ==============================================================================
# END OF FILE. Each numbered section above is a standalone problem — copy just
# the section you need into its own .py file; nothing in it depends on any
# other section.
# ==============================================================================