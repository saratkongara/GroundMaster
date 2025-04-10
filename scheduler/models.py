from dataclasses import dataclass, field
from enum import Enum
from typing import List
from datetime import datetime, timedelta

@dataclass
class Certification:
    id: int
    name: str

class ServiceType(Enum):
    FLIGHT_LEVEL = "F"
    COMMON_LEVEL = "C"
    MULTI_FLIGHT = "M"

class CertificationRequirement(Enum):
    ALL = "All"
    ANY = "Any"

@dataclass
class Service:
    id: int
    name: str
    certifications: List[int]  # List of certification IDs
    certification_requirement: CertificationRequirement
    type: ServiceType
    cross_utilization_limit: int
    exclude_services: List[int] = field(default_factory=list)

@dataclass
class FlightService:
    id: int
    count: int  # Number of staff required for this service
    start: str  # Start time relative to flight (e.g., "A+10")
    end: str    # End time relative to flight (e.g., "D-5")

@dataclass
class Flight:
    number: str
    arrival: str
    departure: str
    flight_services: List[FlightService]

    def get_service_time(self, service_start: str, service_end: str) -> tuple[datetime, datetime]:
        """
        Convert service start and end times (e.g., "A+10", "D-5") into absolute datetime values.
        """
        def resolve_time(time_str: str) -> datetime:
            if time_str.startswith("A"):
                base_time = datetime.strptime(self.arrival, "%H:%M")
            elif time_str.startswith("D"):
                base_time = datetime.strptime(self.departure, "%H:%M")
            else:
                raise ValueError(f"Invalid service time format: {time_str}")

            if "+" in time_str:
                return base_time + timedelta(minutes=int(time_str[2:]))
            elif "-" in time_str:
                return base_time - timedelta(minutes=int(time_str[2:]))
            else:
                return base_time  # Exact A or D time

        return resolve_time(service_start), resolve_time(service_end)

@dataclass
class Shift:
    start: str
    end: str

@dataclass
class Staff:
    id: int
    name: str
    certifications: List[int]  # List of certification IDs
    shifts: List[Shift]

    def is_available_for_service(self, service_start: datetime, service_end: datetime) -> bool:
        """
        Checks if the staff has at least one shift that fully covers the service duration.
        """
        for shift in self.shifts:
            shift_start = datetime.strptime(shift.start, "%H:%M")
            shift_end = datetime.strptime(shift.end, "%H:%M")

            if shift_start <= service_start and shift_end >= service_end:
                return True  # Found a shift that fully covers the service

        return False  # No shift covers the service time

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
class FlightAllocation:
    flight_number: str
    arrival: str
    departure: str
    services: List[FlightServiceAssignment]

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
                staff_names = ", ".join([f"{s.staff_name} ({s.staff_id})" for s in service.assigned_staff])
                print(f"  {service.service_name.ljust(25)}({service.service_type}) : {staff_names if staff_names else 'No staff assigned'}")
            print("\n")