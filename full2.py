import time
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple


# =====================================================================
# 1. TURN-BASED GAME ENGINE
# Patterns: Strategy, Memento, Factory, Command, Chain of Responsibility
# =====================================================================

class BoardMemento:
    def __init__(self, state: List[List[str]]):
        self._state = deepcopy(state)

    def get_state(self) -> List[List[str]]:
        return self._state


class Board:
    def __init__(self, size: int = 3):
        self.size = size
        self.grid = [[' ' for _ in range(size)] for _ in range(size)]

    def place_symbol(self, row: int, col: int, symbol: str) -> bool:
        if 0 <= row < self.size and 0 <= col < self.size and self.grid[row][col] == ' ':
            self.grid[row][col] = symbol
            return True
        return False

    def save(self) -> BoardMemento:
        return BoardMemento(self.grid)

    def restore(self, memento: BoardMemento):
        self.grid = deepcopy(memento.get_state())


class RuleHandler(ABC):
    def __init__(self, next_handler: Optional['RuleHandler'] = None):
        self.next_handler = next_handler

    @abstractmethod
    def check(self, board: Board) -> Optional[str]:
        return self.next_handler.check(board) if self.next_handler else None


class WinHandler(RuleHandler):
    def check(self, board: Board) -> Optional[str]:
        n = board.size
        lines = (
            board.grid
            + [[board.grid[r][c] for r in range(n)] for c in range(n)]
            + [[board.grid[i][i] for i in range(n)], [board.grid[i][n - 1 - i] for i in range(n)]]
        )
        for line in lines:
            if line[0] != ' ' and all(cell == line[0] for cell in line):
                return f"Winner: {line[0]}"
        return super().check(board)


class DrawHandler(RuleHandler):
    def check(self, board: Board) -> Optional[str]:
        if all(cell != ' ' for row in board.grid for cell in row):
            return "Draw"
        return super().check(board)


class MoveStrategy(ABC):
    @abstractmethod
    def get_move(self, board: Board, symbol: str) -> Tuple[int, int]:
        pass


class BasicAIStrategy(MoveStrategy):
    def get_move(self, board: Board, symbol: str) -> Tuple[int, int]:
        for r in range(board.size):
            for c in range(board.size):
                if board.grid[r][c] == ' ':
                    return (r, c)
        return (-1, -1)


class SmartAIStrategy(MoveStrategy):
    def get_move(self, board: Board, symbol: str) -> Tuple[int, int]:
        mid = board.size // 2
        return (mid, mid) if board.grid[mid][mid] == ' ' else BasicAIStrategy().get_move(board, symbol)


class AIStrategyFactory:
    @staticmethod
    def create(difficulty: str) -> MoveStrategy:
        return SmartAIStrategy() if difficulty.lower() == "smart" else BasicAIStrategy()


class MoveCommand:
    def __init__(self, board: Board, row: int, col: int, symbol: str):
        self.board, self.row, self.col, self.symbol = board, row, col, symbol
        self.backup: Optional[BoardMemento] = None

    def execute(self) -> bool:
        self.backup = self.board.save()
        return self.board.place_symbol(self.row, self.col, self.symbol)

    def undo(self):
        if self.backup:
            self.board.restore(self.backup)


class GameEngine:
    def __init__(self, board_size: int = 3, ai_difficulty: str = "smart"):
        self.board = Board(board_size)
        self.ai_strategy = AIStrategyFactory.create(ai_difficulty)
        self.rule_chain = WinHandler(DrawHandler())
        self.history: List[MoveCommand] = []

    def play_turn(self, row: int, col: int, symbol: str = 'X') -> str:
        cmd = MoveCommand(self.board, row, col, symbol)
        if not cmd.execute():
            return "Invalid Move"
        self.history.append(cmd)
        if status := self.rule_chain.check(self.board):
            return status
        ai_r, ai_c = self.ai_strategy.get_move(self.board, 'O')
        if ai_r != -1:
            ai_cmd = MoveCommand(self.board, ai_r, ai_c, 'O')
            ai_cmd.execute()
            self.history.append(ai_cmd)
        return self.rule_chain.check(self.board) or "In Progress"

    def undo(self):
        if self.history:
            self.history.pop().undo()


# =====================================================================
# 2. PAYMENT TRACKING APP - SPLITWISE
# Patterns: Strategy, Builder
# =====================================================================

class User:
    def __init__(self, user_id: str, name: str):
        self.user_id, self.name = user_id, name


class SplitStrategy(ABC):
    @abstractmethod
    def calculate_splits(self, amount: float, participants: List[User], metadata: Dict[str, float]) -> Dict[str, float]:
        pass


class EqualSplit(SplitStrategy):
    def calculate_splits(self, amount: float, participants: List[User], metadata: Dict[str, float]) -> Dict[str, float]:
        share = round(amount / len(participants), 2)
        return {u.user_id: share for u in participants}


class ExactSplit(SplitStrategy):
    def calculate_splits(self, amount: float, participants: List[User], metadata: Dict[str, float]) -> Dict[str, float]:
        if round(sum(metadata.values()), 2) != round(amount, 2):
            raise ValueError("Exact splits must sum to total amount.")
        return metadata


class PercentSplit(SplitStrategy):
    def calculate_splits(self, amount: float, participants: List[User], metadata: Dict[str, float]) -> Dict[str, float]:
        if round(sum(metadata.values()), 2) != 100.0:
            raise ValueError("Percentages must sum to 100.")
        return {uid: round(amount * (pct / 100.0), 2) for uid, pct in metadata.items()}


class Expense:
    def __init__(self, paid_by: User, amount: float, participants: List[User], strategy: SplitStrategy, metadata: Dict[str, float]):
        self.paid_by, self.amount, self.participants, self.strategy, self.metadata = paid_by, amount, participants, strategy, metadata


class ExpenseBuilder:
    def __init__(self):
        self._paid_by: Optional[User] = None
        self._amount: float = 0.0
        self._participants: List[User] = []
        self._strategy: SplitStrategy = EqualSplit()
        self._metadata: Dict[str, float] = {}

    def paid_by(self, user: User) -> 'ExpenseBuilder':
        self._paid_by = user
        return self

    def amount(self, amount: float) -> 'ExpenseBuilder':
        self._amount = amount
        return self

    def participants(self, users: List[User]) -> 'ExpenseBuilder':
        self._participants = users
        return self

    def strategy(self, strategy: SplitStrategy, metadata: Optional[Dict[str, float]] = None) -> 'ExpenseBuilder':
        self._strategy, self._metadata = strategy, metadata or {}
        return self

    def build(self) -> Expense:
        if not self._paid_by or not self._participants or self._amount <= 0:
            raise ValueError("Incomplete expense details.")
        return Expense(self._paid_by, self._amount, self._participants, self._strategy, self._metadata)


class ExpenseManager:
    def __init__(self):
        self.balances: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def add_expense(self, expense: Expense):
        splits = expense.strategy.calculate_splits(expense.amount, expense.participants, expense.metadata)
        for uid, owed in splits.items():
            if uid != expense.paid_by.user_id:
                self.balances[uid][expense.paid_by.user_id] += owed
                self.balances[expense.paid_by.user_id][uid] -= owed

    def get_simplified_debts(self) -> List[str]:
        net: Dict[str, float] = defaultdict(float)
        for u1, debts in self.balances.items():
            for _, amt in debts.items():
                net[u1] -= amt
        debtors = [[u, -b] for u, b in net.items() if b < -0.01]
        creditors = [[u, b] for u, b in net.items() if b > 0.01]
        settlements, i, j = [], 0, 0
        while i < len(debtors) and j < len(creditors):
            amt = min(debtors[i][1], creditors[j][1])
            settlements.append(f"{debtors[i][0]} pays {creditors[j][0]}: ${amt:.2f}")
            debtors[i][1] -= amt
            creditors[j][1] -= amt
            if debtors[i][1] < 0.01:
                i += 1
            if creditors[j][1] < 0.01:
                j += 1

        return settlements


# =====================================================================
# 3. CACHE (Thread-Safe LRU Cache + TTL)
# Patterns: Strategy, Doubly Linked List + HashMap
# =====================================================================

class CacheNode:
    def __init__(self, key: Any, value: Any):
        self.key, self.value = key, value
        self.prev: Optional['CacheNode'] = None
        self.next: Optional['CacheNode'] = None


class EvictionPolicy(ABC):
    @abstractmethod
    def key_accessed(self, key: Any):
        pass

    @abstractmethod
    def evict_key(self) -> Any:
        pass

    @abstractmethod
    def remove_key(self, key: Any):
        pass


class LRUEvictionPolicy(EvictionPolicy):
    def __init__(self):
        self.head, self.tail = CacheNode(None, None), CacheNode(None, None)
        self.head.next, self.tail.prev = self.tail, self.head
        self.node_map: Dict[Any, CacheNode] = {}

    def _unlink(self, node: CacheNode):
        node.prev.next, node.next.prev = node.next, node.prev

    def _insert_front(self, node: CacheNode):
        node.next, node.prev = self.head.next, self.head
        self.head.next.prev = self.head.next = node

    def key_accessed(self, key: Any):
        if key in self.node_map:
            self._unlink(self.node_map[key])
            self._insert_front(self.node_map[key])
        else:
            self.node_map[key] = CacheNode(key, None)
            self._insert_front(self.node_map[key])

    def evict_key(self) -> Any:
        lru = self.tail.prev
        if lru == self.head:
            return None
        self._unlink(lru)
        del self.node_map[lru.key]
        return lru.key

    def remove_key(self, key: Any):
        if key in self.node_map:
            self._unlink(self.node_map.pop(key))


class Cache:
    def __init__(self, capacity: int, eviction_policy: Optional[EvictionPolicy] = None):
        self.capacity = capacity
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()
        self.storage: Dict[Any, Tuple[Any, Optional[float]]] = {}
        self.lock = threading.Lock()

    def get(self, key: Any) -> Any:
        with self.lock:
            if key not in self.storage:
                return -1
            val, exp = self.storage[key]
            if exp is not None and time.monotonic() > exp:
                del self.storage[key]
                self.eviction_policy.remove_key(key)
                return -1
            self.eviction_policy.key_accessed(key)
            return val

    def put(self, key: Any, value: Any, ttl_seconds: Optional[float] = None):
        with self.lock:
            if key not in self.storage and len(self.storage) >= self.capacity:
                if (evicted := self.eviction_policy.evict_key()) is not None:
                    del self.storage[evicted]
            self.storage[key] = (value, time.monotonic() + ttl_seconds if ttl_seconds else None)
            self.eviction_policy.key_accessed(key)


# =====================================================================
# 4. EVENT BUS (Thread-Safe Pub/Sub + Retries + Dead-Letter Queue)
# Patterns: Observer / Pub-Sub
# =====================================================================

class Event:
    def __init__(self, topic: str, payload: Any):
        self.topic, self.payload = topic, payload


class EventBus:
    def __init__(self, max_workers: int = 4, max_retries: int = 2):
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)
        self.dead_letter_queue: List[Tuple[Event, str]] = []
        self.max_retries = max_retries
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def subscribe(self, topic: str, handler: Callable[[Event], None]):
        with self.lock:
            self.subscribers[topic].append(handler)

    def publish(self, event: Event):
        with self.lock:
            handlers = list(self.subscribers[event.topic])
        for handler in handlers:
            self.executor.submit(self._execute, handler, event)

    def _execute(self, handler: Callable[[Event], None], event: Event):
        err = ""
        for _ in range(self.max_retries + 1):
            try:
                handler(event)
                return
            except Exception as e:
                err = str(e)
        with self.lock:
            self.dead_letter_queue.append((event, err))

    def shutdown(self):
        self.executor.shutdown(wait=True)


# =====================================================================
# 5. RATE LIMITER (Token Bucket & Sliding Window Log)
# Patterns: Strategy
# =====================================================================

class RateLimiterStrategy(ABC):
    @abstractmethod
    def allow_request(self, client_id: str) -> bool:
        pass


class TokenBucketRateLimiter(RateLimiterStrategy):
    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self.capacity, self.refill_rate = float(capacity), refill_rate_per_sec
        self.buckets: Dict[str, Tuple[float, float]] = {}
        self.lock = threading.Lock()

    def allow_request(self, client_id: str) -> bool:
        with self.lock:
            now = time.monotonic()
            tokens, last = self.buckets.get(client_id, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill_rate)
            if tokens >= 1.0:
                self.buckets[client_id] = (tokens - 1.0, now)
                return True
            self.buckets[client_id] = (tokens, now)
            return False


class SlidingWindowRateLimiter(RateLimiterStrategy):
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests, self.window_seconds = max_requests, window_seconds
        self.logs: Dict[str, deque] = {}
        self.lock = threading.Lock()

    def allow_request(self, client_id: str) -> bool:
        with self.lock:
            now = time.monotonic()
            q = self.logs.setdefault(client_id, deque())
            while q and (now - q[0]) >= self.window_seconds:
                q.popleft()
            if len(q) < self.max_requests:
                q.append(now)
                return True
            return False


class RateLimiter:
    def __init__(self, strategy: RateLimiterStrategy):
        self.strategy = strategy

    def is_allowed(self, client_id: str) -> bool:
        return self.strategy.allow_request(client_id)


# =====================================================================
# DEMO RUNNER
# =====================================================================

if __name__ == "__main__":
    game = GameEngine()
    print("Game:", game.play_turn(0, 0, 'X'), game.board.grid)

    alice, bob = User("Alice", "Alice"), User("Bob", "Bob")
    em = ExpenseManager()
    em.add_expense(ExpenseBuilder().paid_by(alice).amount(100).participants([alice, bob]).build())
    print("Splitwise:", em.get_simplified_debts())

    cache = Cache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.put("c", 3)
    print("Cache 'b' evicted:", cache.get("b"), "| 'a':", cache.get("a"))

    bus = EventBus()
    bus.subscribe("order", lambda e: print("Event:", e.payload))
    bus.publish(Event("order", {"id": 1}))
    bus.shutdown()

    rl = RateLimiter(SlidingWindowRateLimiter(2, 5.0))
    print("RateLimiter:", rl.is_allowed("u1"), rl.is_allowed("u1"), rl.is_allowed("u1"))
