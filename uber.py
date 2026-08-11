from abc import ABC, abstractmethod
from enum import Enum
from math import sqrt
from typing import List

# ==============================================================================
# 1. CORE DATA OBJECTS & LIFECYCLE ENUMS
# ==============================================================================

class Location:
    def __init__(self, latitude: float, longitude: float):
        self.__latitude = latitude
        self.__longitude = longitude

    def get_latitude(self) -> float:
        return self.__latitude

    def get_longitude(self) -> float:
        return self.__longitude

    def calculate_distance(self, location2: 'Location') -> float:
        dx = self.get_latitude() - location2.get_latitude()
        dy = self.get_longitude() - location2.get_longitude()
        return sqrt(dx * dx + dy * dy)


class RideStatus(Enum):
    SCHEDULED = "Scheduled"
    ONGOING = "Ongoing"
    COMPLETED = "Completed"


# ==============================================================================
# 2. USER & OBSERVER PATTERN HIERARCHY
# ==============================================================================

class User(ABC):
    def __init__(self, name: str, email: str, location: Location):
        self.name = name
        self.email = email
        self.location = location

    def get_location(self) -> Location:
        return self.location

    def set_location(self, location: Location):
        self.location = location

    @abstractmethod
    def notify(self, message: str):
        pass


class Passenger(User):
    def notify(self, message: str):
        print(f"Notify to Passenger {self.name}: {message}")


# ==============================================================================
# 3. VEHICLE OBJECT MODEL HIERARCHY
# ==============================================================================

class Vehicle(ABC):
    def __init__(self, number_plate: str):
        self.number_plate = number_plate

    @abstractmethod
    def get_fare_amount(self) -> float:
        pass


class Car(Vehicle):
    def get_fare_amount(self) -> float:
        return 20.0


class Bike(Vehicle):
    def get_fare_amount(self) -> float:
        return 10.0


class Driver(User):
    def __init__(self, name: str, email: str, location: Location, vehicle: Vehicle):
        super().__init__(name, email, location)
        self.__vehicle = vehicle

    def get_vehicle(self) -> Vehicle:
        return self.__vehicle

    def notify(self, message: str):
        print(f"Notify to Driver {self.name}: {message}")


# ==============================================================================
# 4. STRATEGY DESIGN PATTERN (DYNAMIC FARE SYSTEM)
# ==============================================================================

class FairStrategy(ABC):
    @abstractmethod
    def calculate_fair(self, vehicle: Vehicle, distance: float) -> float:
        pass


class StandardFairStrategy(FairStrategy):
    def calculate_fair(self, vehicle: Vehicle, distance: float) -> float:
        return vehicle.get_fare_amount() * distance


class SharedFairStrategy(FairStrategy):
    def calculate_fair(self, vehicle: Vehicle, distance: float) -> float:
        return vehicle.get_fare_amount() * distance * 0.5


class LuxuryFairStrategy(FairStrategy):
    def calculate_fair(self, vehicle: Vehicle, distance: float) -> float:
        return vehicle.get_fare_amount() * distance * 1.5


# ==============================================================================
# 5. CORE RIDE LIFE WORKFLOW MODEL
# ==============================================================================

class Ride:
    def __init__(self, passenger: Passenger, driver: Driver, distance: float, fair_strategy: FairStrategy):
        self.passenger = passenger
        self.driver = driver
        self.distance = distance
        self.fair_strategy = fair_strategy
        self.__fair = 0.0
        self.status = RideStatus.SCHEDULED

    def calculate_fair(self):
        self.__fair = self.fair_strategy.calculate_fair(self.driver.get_vehicle(), self.distance)

    def get_ride_fair(self) -> float:
        return self.__fair

    def update_status(self, new_ride_status: RideStatus):
        self.status = new_ride_status
        self.__notify_users(new_ride_status)

    def __notify_users(self, ride_status: RideStatus):
        self.driver.notify(f"Your ride status is {ride_status.value}")
        self.passenger.notify(f"Your ride status is {ride_status.value}")


# ==============================================================================
# 6. ROUTING AND ALLOCATION MATCHER SERVICE
# ==============================================================================

class RideMatchingService:
    def __init__(self):
        self.__available_drivers: List[Driver] = []

    def add_driver(self, driver: Driver):
        self.__available_drivers.append(driver)

    def __find_nearest_driver(self, passenger_location: Location) -> Driver:
        assign_driver = None
        min_distance = float('inf')

        for driver in self.__available_drivers:
            distance = driver.get_location().calculate_distance(passenger_location)
            if distance < min_distance:
                min_distance = distance
                assign_driver = driver
        return assign_driver

    def request_ride(self, passenger: Passenger, distance: float, fair_strategy: FairStrategy):
        if len(self.__available_drivers) == 0:
            passenger.notify("No drivers available")
            return

        nearest_driver = self.__find_nearest_driver(passenger.get_location())
        self.__available_drivers.remove(nearest_driver)

        # Build ride orchestration entity
        ride = Ride(passenger, nearest_driver, distance, fair_strategy)
        ride.calculate_fair()

        passenger.notify(f"Ride scheduled with fair Rs.{ride.get_ride_fair()}")
        nearest_driver.notify(f"You have one new ride for Rs.{ride.get_ride_fair()}")

        # Process Journey Sequence Status 
        ride.update_status(RideStatus.ONGOING)
        ride.update_status(RideStatus.COMPLETED)

        # Release driver back to the open registry pool
        self.__available_drivers.append(nearest_driver)


# ==============================================================================
# 7. MAIN CLIENT RUNTIME ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Create coordinate pairs
    loc1 = Location(12.9716, 77.5946)
    loc2 = Location(12.9716, 77.5946)  # Stationed together to create 0km arrival variance

    # Instantiate vehicle types
    audi = Car("KA-01-MG-1234")
    hero = Bike("KA-02-EE-5678")

    # Set up system users
    driver1 = Driver("Alice", "alice@example.com", loc1, audi)
    passenger1 = Passenger("Aniruddh", "aniruddh@gmail.com", loc2)

    # Initialize app matching core engine
    matcher = RideMatchingService()
    matcher.add_driver(driver1)

    print("--- Execution Workflow Start ---")
    luxury_pricing = LuxuryFairStrategy()
    
    # Process allocation lifecycle
    matcher.request_ride(passenger1, 50.0, luxury_pricing)
