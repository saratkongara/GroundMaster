from dataclasses import dataclass

@dataclass
class FlightService:
    id: int
    count: int  # Number of staff required for this service
    start: str  # Start time relative to flight (e.g., "A+10")
    end: str    # End time relative to flight (e.g., "D-5")
