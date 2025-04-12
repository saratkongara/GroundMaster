from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta
from .flight_service import FlightService

@dataclass
class Flight:
    number: str
    arrival: str
    departure: str
    flight_services: List[FlightService]
    bay_number: str  # Bay number where the flight is located (e.g., "A1", "B2")

    def __post_init__(self):
        # Parse arrival and departure times into datetime objects
        self.arrival_time = datetime.strptime(self.arrival, "%H:%M")
        self.departure_time = datetime.strptime(self.departure, "%H:%M")
    
    def get_service_time(self, service_start: str, service_end: str) -> tuple[datetime, datetime]:
        """
        Convert service start and end times (e.g., "A+10", "D-5") into absolute datetime values.
        """
        def resolve_time(time_str: str) -> datetime:
            if time_str.startswith("A"):
                base_time = self.arrival_time
            elif time_str.startswith("D"):
                base_time = self.departure_time
            else:
                raise ValueError(f"Invalid service time format: {time_str}")

            if "+" in time_str:
                return base_time + timedelta(minutes=int(time_str[2:]))
            elif "-" in time_str:
                return base_time - timedelta(minutes=int(time_str[2:]))
            else:
                return base_time  # Exact A or D time

        return resolve_time(service_start), resolve_time(service_end)