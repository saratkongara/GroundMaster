import logging
from .base_constraint import Constraint
from scheduler.models.base import ServiceType
from datetime import timedelta

class FlightTransitionConstraint(Constraint):
    """
    Constraint to ensure that staff members cannot be assigned to overlapping flight services:
    1. Only checks flights marked as overlapping in overlapping_flights_map
    2. Skips service pairs where staff isn't available during the service times
    3. Skips service pairs where staff lacks required certifications
    """
    def __init__(self, flights, roster, service_map, flight_map, travel_time_map, overlapping_flights_map, overlap_tolerance_buffer):
        self.flights = flights
        self.roster = roster
        self.service_map = service_map
        self.flight_map = flight_map
        self.travel_time_map = travel_time_map
        self.overlapping_flights_map = overlapping_flights_map
        self.overlap_tolerance_buffer = overlap_tolerance_buffer

    def apply(self, model, assignments):
        logging.debug("Adding flight transition constraints with availability and certification checks...")

        for staff in self.roster:
            for flight_a in self.flights:
                for flight_b_num in self.overlapping_flights_map.get(flight_a.number, []):
                    flight_b = self.flight_map[flight_b_num]
                    travel_time = self.travel_time_map.get(
                        (flight_a.bay_number, flight_b.bay_number), 0)

                    for service_a in flight_a.flight_services:
                        if self.service_map[service_a.id].type == ServiceType.MULTI_FLIGHT:
                            continue

                        # Get service and check staff eligibility
                        service_a_obj = self.service_map[service_a.id]
                        a_start, a_end = flight_a.get_service_time(service_a.start, service_a.end)
                        
                        if not (staff.is_available_for_service(a_start, a_end) and 
                            staff.can_perform_service(service_a_obj)):
                            continue

                        adjusted_a_end = a_end + timedelta(minutes=travel_time)

                        for service_b in flight_b.flight_services:
                            if self.service_map[service_b.id].type == ServiceType.MULTI_FLIGHT:
                                continue

                            # Get service and check staff eligibility
                            service_b_obj = self.service_map[service_b.id]
                            b_start, b_end = flight_b.get_service_time(service_b.start, service_b.end)
                            
                            if not (staff.is_available_for_service(b_start, b_end) and 
                                staff.can_perform_service(service_b_obj)):
                                continue

                            if adjusted_a_end > b_start + timedelta(minutes=self.overlap_tolerance_buffer):
                                var_a = assignments.get((flight_a.number, service_a.id, staff.id))
                                var_b = assignments.get((flight_b.number, service_b.id, staff.id))
                                
                                model.Add(var_a + var_b <= 1)
                                logging.debug(
                                    f"Conflict: Staff {staff.id} cannot serve both "
                                    f"{service_a.id}@{flight_a.number}(ends {a_end.time()}+{travel_time}min) "
                                    f"and {service_b.id}@{flight_b.number}(starts {b_start.time()})"
                                )