from dataclasses import dataclass
from typing import List

@dataclass
class StaffInfo:
    staff_id: int
    staff_name: str

@dataclass
class ServiceAllocation:
    service_id: int
    service_name: str
    service_type: str
    staff_allocation: List[StaffInfo]
    required_staff_count: int

@dataclass
class FlightAllocation:
    flight_number: str
    arrival: str
    departure: str
    services: List[ServiceAllocation]

@dataclass
class Schedule:
    allocations: List[FlightAllocation]

    def display(self):
        """Displays the generated schedule flight-wise in a readable format."""
        print("\n=== Services Schedule ===\n")
        for allocation in self.allocations:
            print(f"Flight {allocation.flight_number} | Arrival: {allocation.arrival} | Departure: {allocation.departure}")
            print("-" * 60)
            for service in allocation.services:
                staff_names = ", ".join([f"{s.staff_name} ({s.staff_id})" for s in service.staff_allocation])
                print(f"  {service.service_name.ljust(25)}({service.service_type}) : {staff_names if staff_names else 'No staff assigned'}")
            print("\n")