import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from scheduler.models import Flight, Bay, Service, ServiceType

class OverlapDetectionService:
    """
    Detects potentially overlapping flights considering:
    - Flight service time windows
    - Bay travel times
    - Allowed overlap tolerance buffer
    
    Attributes:
        flights: List of flights to analyze
        bays: Mapping of bay numbers to Bay objects
        service_map: Mapping of service IDs to Service objects
        buffer_minutes: Allowed overlap buffer in minutes
    """
    
    def __init__(
        self,
        flights: List[Flight],
        travel_time_map: Dict[Tuple[str, str], int],
        service_map: Dict[str, Service],
        buffer_minutes: int
    ):
        self.flights = flights
        self.travel_time_map = travel_time_map
        self.service_map = service_map
        self.buffer_minutes = buffer_minutes

    def detect_overlaps(self) -> Dict[str, List[str]]:
        """
        Build mapping of flights to their potentially overlapping subsequent flights.
        
        Returns:
            Dict mapping flight numbers to lists of overlapping flight numbers,
            where overlaps always point to later flights in the schedule.
        """
        logging.debug("Building flight overlap map...")

        # Sort flights chronologically to enable single-pass comparison
        sorted_flights = sorted(self.flights, key=lambda f: f.arrival_time)
        overlap_map = defaultdict(list)

        for i, flight_a in enumerate(sorted_flights):
            a_end = self._get_latest_service_end(flight_a)
            
            # Only check future flights (j > i)
            for j in range(i + 1, len(sorted_flights)):
                flight_b = sorted_flights[j]
                b_start = self._get_earliest_service_start(flight_b)
                
                if self._has_temporal_conflict(flight_a, flight_b, a_end, b_start):
                    overlap_map[flight_a.number].append(flight_b.number)
                else:
                    break  # No overlap with this or subsequent flights

        return overlap_map

    def _get_latest_service_end(self, flight: Flight) -> datetime:
        """Calculate latest non-MultiFlight service end time for a flight."""
        services = [
            fs for fs in flight.flight_services
            if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
        ]
        return (
            max(flight.get_service_time(fs.start, fs.end)[1] for fs in services)
            if services # Only calculate max if non-MultiFlight services exist
            else flight.departure_time # Fallback to flight departure time
        )

    def _get_earliest_service_start(self, flight: Flight) -> datetime:
        """Calculate earliest non-MultiFlight service start time for a flight."""
        services = [
            fs for fs in flight.flight_services
            if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
        ]
        return (
            min(flight.get_service_time(fs.start, fs.end)[0] for fs in services)
            if services # Only calculate min if non-MultiFlight services exist
            else flight.arrival_time # Fallback to flight arrival time
        )

    def _has_temporal_conflict(
        self,
        flight_a: Flight,
        flight_b: Flight,
        a_end: datetime,
        b_start: datetime
    ) -> bool:
        """Determine if two flights have scheduling conflict considering travel."""
        travel_time = self.travel_time_map.get(
                    (flight_a.bay_number, flight_b.bay_number), 0)
        required_gap = max(travel_time - self.buffer_minutes, 0)
        
        conflict = a_end + timedelta(minutes=required_gap) > b_start
        
        if conflict:
            logging.debug(
                f"Overlap detected: Flight {flight_a.number} (ends {a_end.time()}) "
                f"conflicts with Flight {flight_b.number} (starts {b_start.time()}) "
                f"with {required_gap} min required gap "
                f"(travel: {travel_time} min, buffer: {self.buffer_minutes} min)"
            )
        
        return conflict