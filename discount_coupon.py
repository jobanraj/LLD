from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Optional


# ----------------------------
# Discount Strategy (Strategy Pattern)
# ----------------------------
class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, base_amount: float) -> float:
        pass


class FlatDiscountStrategy(DiscountStrategy):
    def __init__(self, amount: float):
        self.amount = amount

    def calculate(self, base_amount: float) -> float:
        return min(self.amount, base_amount)


class PercentageDiscountStrategy(DiscountStrategy):
    def __init__(self, percent: float):
        self.percent = percent

    def calculate(self, base_amount: float) -> float:
        return (self.percent / 100.0) * base_amount


class PercentageWithCapStrategy(DiscountStrategy):
    def __init__(self, percent: float, cap_val: float):
        self.percent = percent
        self.cap = cap_val

    def calculate(self, base_amount: float) -> float:
        disc = (self.percent / 100.0) * base_amount
        return self.cap if disc > self.cap else disc


class StrategyType(Enum):
    FLAT = auto()
    PERCENT = auto()
    PERCENT_WITH_CAP = auto()


# ----------------------------
# DiscountStrategyManager (Singleton Pattern)
# ----------------------------
class DiscountStrategyManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DiscountStrategyManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def get_strategy(self, strategy_type: StrategyType, param1: float, param2: float = 0.0) -> Optional[DiscountStrategy]:
        if strategy_type == StrategyType.FLAT:
            return FlatDiscountStrategy(param1)
        elif strategy_type == StrategyType.PERCENT:
            return PercentageDiscountStrategy(param1)
        elif strategy_type == StrategyType.PERCENT_WITH_CAP:
            return PercentageWithCapStrategy(param1, param2)
        return None


# ----------------------------
# Cart and Product Classes
# ----------------------------
class Product:
    def __init__(self, name: str, category: str, price: float):
        self._name = name
        self._category = category
        self._price = price

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    @property
    def price(self) -> float:
        return self._price


class CartItem:
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = quantity

    def item_total(self) -> float:
        return self._product.price * self._quantity

    @property
    def product(self) -> Product:
        return self._product


class Cart:
    def __init__(self):
        self._items: List[CartItem] = []
        self._original_total: float = 0.0
        self._current_total: float = 0.0
        self.loyalty_member: bool = False
        self.payment_bank: str = ""

    def add_product(self, prod: Product, qty: int):
        item = CartItem(prod, qty)
        self._items.append(item)
        self._original_total += item.item_total()
        self._current_total += item.item_total()

    @property
    def original_total(self) -> float:
        return self._original_total

    @property
    def current_total(self) -> float:
        return self._current_total

    def apply_discount(self, d: float):
        self._current_total -= d
        if self._current_total < 0:
            self._current_total = 0.0

    @property
    def items(self) -> List[CartItem]:
        return self._items


# ----------------------------
# Coupon Base Class (Chain of Responsibility)
# ----------------------------
class Coupon(ABC):
    def __init__(self):
        self._next: Optional[Coupon] = None

    @property
    def next(self) -> Optional['Coupon']:
        return self._next

    @next.setter
    def next(self, nxt: Optional['Coupon']):
        self._next = nxt

    def apply_discount(self, cart: Cart):
        if self.is_applicable(cart):
            discount = self.get_discount(cart)
            cart.apply_discount(discount)
            print(f"{self.name()} applied: {discount}")
            if not self.is_combinable():
                return

        if self._next is not None:
            self._next.apply_discount(cart)

    @abstractmethod
    def is_applicable(self, cart: Cart) -> bool:
        pass

    @abstractmethod
    def get_discount(self, cart: Cart) -> float:
        pass

    def is_combinable(self) -> bool:
        return True

    @abstractmethod
    def name(self) -> str:
        pass


# ----------------------------
# Concrete Coupons
# ----------------------------
class SeasonalOffer(Coupon):
    def __init__(self, percent: float, category: str):
        super().__init__()
        self.percent = percent
        self.category = category
        self.strat = DiscountStrategyManager.get_instance().get_strategy(
            StrategyType.PERCENT, self.percent
        )

    def is_applicable(self, cart: Cart) -> bool:
        return any(item.product.category == self.category for item in cart.items)

    def get_discount(self, cart: Cart) -> float:
        subtotal = sum(item.item_total() for item in cart.items if item.product.category == self.category)
        return self.strat.calculate(subtotal) if self.strat else 0.0

    def name(self) -> str:
        return f"Seasonal Offer {int(self.percent)}% off {self.category}"


class LoyaltyDiscount(Coupon):
    def __init__(self, percent: float):
        super().__init__()
        self.percent = percent
        self.strat = DiscountStrategyManager.get_instance().get_strategy(
            StrategyType.PERCENT, self.percent
        )

    def is_applicable(self, cart: Cart) -> bool:
        return cart.loyalty_member

    def get_discount(self, cart: Cart) -> float:
        return self.strat.calculate(cart.current_total) if self.strat else 0.0

    def name(self) -> str:
        return f"Loyalty Discount {int(self.percent)}% off"


class BulkPurchaseDiscount(Coupon):
    def __init__(self, threshold: float, flat_off: float):
        super().__init__()
        self.threshold = threshold
        self.flat_off = flat_off
        self.strat = DiscountStrategyManager.get_instance().get_strategy(
            StrategyType.FLAT, self.flat_off
        )

    def is_applicable(self, cart: Cart) -> bool:
        return cart.original_total >= self.threshold

    def get_discount(self, cart: Cart) -> float:
        return self.strat.calculate(cart.current_total) if self.strat else 0.0

    def name(self) -> str:
        return f"Bulk Purchase Rs {int(self.flat_off)} off over {int(self.threshold)}"


class BankingCoupon(Coupon):
    def __init__(self, bank: str, min_spend: float, percent: float, off_cap: float):
        super().__init__()
        self.bank = bank
        self.min_spend = min_spend
        self.percent = percent
        self.off_cap = off_cap
        self.strat = DiscountStrategyManager.get_instance().get_strategy(
            StrategyType.PERCENT_WITH_CAP, self.percent, self.off_cap
        )

    def is_applicable(self, cart: Cart) -> bool:
        return cart.payment_bank == self.bank and cart.current_total >= self.min_spend

    def get_discount(self, cart: Cart) -> float:
        return self.strat.calculate(cart.current_total) if self.strat else 0.0

    def name(self) -> str:
        return f"Banking Coupon ({self.bank}): {int(self.percent)}% off up to {int(self.off_cap)}"
