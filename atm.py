from abc import ABC, abstractmethod
import random
from enum import Enum, auto

# ----------------------------
# Data structure for payment details
# ----------------------------
class PaymentRequest:
    def __init__(self, sender: str, receiver: str, amt: float, curr: str):
        self.sender = sender
        self.receiver = receiver
        self.amount = amt
        self.currency = curr

# ----------------------------
# Banking System interface and implementations (Strategy Pattern)
# ----------------------------
class BankingSystem(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> bool:
        pass

class PaytmBankingSystem(BankingSystem):
    def process_payment(self, amount: float) -> bool:
        # Simulate 80% success
        return random.randint(0, 99) < 80

class RazorpayBankingSystem(BankingSystem):
    def process_payment(self, amount: float) -> bool:
        print(f"[BankingSystem-Razorpay] Processing payment of {amount}...")
        # Simulate 90% success
        return random.randint(0, 99) < 90

# ----------------------------
# Abstract base class for Payment Gateway (Template Method Pattern)
# ----------------------------
class PaymentGateway(ABC):
    def __init__(self):
        self.banking_system = None

    # Template method defining the standard payment flow
    def process_payment(self, request: PaymentRequest) -> bool:
        if not self._validate_payment(request):
            print(f"[PaymentGateway] Validation failed for {request.sender}.")
            return False
        if not self._initiate_payment(request):
            print(f"[PaymentGateway] Initiation failed for {request.sender}.")
            return False
        if not self._confirm_payment(request):
            print(f"[PaymentGateway] Confirmation failed for {request.sender}.")
            return False
        return True

    @abstractmethod
    def _validate_payment(self, request: PaymentRequest) -> bool:
        pass

    @abstractmethod
    def _initiate_payment(self, request: PaymentRequest) -> bool:
        pass

    @abstractmethod
    def _confirm_payment(self, request: PaymentRequest) -> bool:
        pass

# ----------------------------
# Concrete Payment Gateway for Paytm
# ----------------------------
class PaytmGateway(PaymentGateway):
    def __init__(self):
        super().__init__()
        self.banking_system = PaytmBankingSystem()

    def _validate_payment(self, request: PaymentRequest) -> bool:
        print(f"[Paytm] Validating payment for {request.sender}.")
        if request.amount <= 0 or request.currency != "INR":
            return False
        return True

    def _initiate_payment(self, request: PaymentRequest) -> bool:
        print(f"[Paytm] Initiating payment of {request.amount} {request.currency} for {request.sender}.")
        return self.banking_system.process_payment(request.amount)

    def _confirm_payment(self, request: PaymentRequest) -> bool:
        print(f"[Paytm] Confirming payment for {request.sender}.")
        return True

# ----------------------------
# Concrete Payment Gateway for Razorpay
# ----------------------------
class RazorpayGateway(PaymentGateway):
    def __init__(self):
        super().__init__()
        self.banking_system = RazorpayBankingSystem()

    def _validate_payment(self, request: PaymentRequest) -> bool:
        print(f"[Razorpay] Validating payment for {request.sender}.")
        if request.amount <= 0:
            return False
        return True

    def _initiate_payment(self, request: PaymentRequest) -> bool:
        print(f"[Razorpay] Initiating payment of {request.amount} {request.currency} for {request.sender}.")
        return self.banking_system.process_payment(request.amount)

    def _confirm_payment(self, request: PaymentRequest) -> bool:
        print(f"[Razorpay] Confirming payment for {request.sender}.")
        return True

# ----------------------------
# Proxy class with retries (Proxy Pattern)
# ----------------------------
class PaymentGatewayProxy(PaymentGateway):
    def __init__(self, gateway: PaymentGateway, max_retries: int):
        super().__init__()
        self._real_gateway = gateway
        self._retries = max_retries

    def process_payment(self, request: PaymentRequest) -> bool:
        result = False
        for attempt in range(self._retries):
            if attempt > 0:
                print(f"[Proxy] Retrying payment (attempt {attempt + 1}) for {request.sender}.")
            result = self._real_gateway.process_payment(request)
            if result:
                break
        if not result:
            print(f"[Proxy] Payment failed after {self._retries} attempts for {request.sender}.")
        return result

    def _validate_payment(self, request: PaymentRequest) -> bool:
        return self._real_gateway._validate_payment(request)

    def _initiate_payment(self, request: PaymentRequest) -> bool:
        return self._real_gateway._initiate_payment(request)

    def _confirm_payment(self, request: PaymentRequest) -> bool:
        return self._real_gateway._confirm_payment(request)

# ----------------------------
# Gateway Factory (Singleton via Python module instantiation)
# ----------------------------
class GatewayType(Enum):
    PAYTM = auto()
    RAZORPAY = auto()

class GatewayFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GatewayFactory, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def get_gateway(self, gateway_type: GatewayType) -> PaymentGateway:
        if gateway_type == GatewayType.PAYTM:
            real_gateway = PaytmGateway()
            return PaymentGatewayProxy(real_gateway, 3)
        else:
            real_gateway = RazorpayGateway()
            return PaymentGatewayProxy(real_gateway, 1)

# ----------------------------
# Unified API service (Singleton)
# ----------------------------
class PaymentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PaymentService, cls).__new__(cls)
            cls._instance.gateway = None
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def set_gateway(self, g: PaymentGateway):
        self.gateway = g

    def process_payment(self, request: PaymentRequest) -> bool:
        if self.gateway is None:
            print("[PaymentService] No payment gateway selected.")
            return False
        return self.gateway.process_payment(request)

# ----------------------------
# Controller class for client requests (Singleton)
# ----------------------------
class PaymentController:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PaymentController, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def handle_payment(self, gateway_type: GatewayType, req: PaymentRequest) -> bool:
        factory = GatewayFactory.get_instance()
        gateway = factory.get_gateway(gateway_type)
        
        service = PaymentService.get_instance()
        service.set_gateway(gateway)
        
        return service.process_payment(req)

# ----------------------------
# Execution Example
# ----------------------------
if __name__ == "__main__":
    controller = PaymentController.get_instance()
    request = PaymentRequest("Alice", "Bob", 500.0, "INR")
    
    print("--- Executing Paytm Transaction ---")
    controller.handle_payment(GatewayType.PAYTM, request)
