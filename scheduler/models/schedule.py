from dataclasses import dataclass
from typing import List

@dataclass
class StaffAssignment:
    staff_id: int
    staff_name: str

@dataclass
class FlightServiceAssignment:
    service_id: int
    service_name: str
    service_type: str
    assigned_staff: List[StaffAssignment]
    required_staff_count: int

@dataclass
class FlightAssignment:
    flight_number: str
    arrival: str
    departure: str
    services: List[FlightServiceAssignment]

@dataclass
class Schedule:
    assignments: List[FlightAssignment]

    def display(self):
        """Displays the generated schedule flight-wise in a readable format."""
        print("\n=== Services Schedule ===\n")
        for allocation in self.assignments:
            print(f"Flight {allocation.flight_number} | Arrival: {allocation.arrival} | Departure: {allocation.departure}")
            print("-" * 60)
            for service in allocation.services:
                staff_names = ", ".join([f"{s.staff_name} ({s.staff_id})" for s in service.assigned_staff])
                print(f"  {service.service_name.ljust(25)}({service.service_type}) : {staff_names if staff_names else 'No staff assigned'}")
            print("\n")