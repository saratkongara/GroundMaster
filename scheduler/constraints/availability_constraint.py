import logging
from .base_constraint import Constraint

class AvailabilityConstraint(Constraint):
    """
    Constraint to ensure that staff are only assigned to services during their available shifts.
    """
    def __init__(self, flights, roster):
        self.flights = flights
        self.roster = roster

    def apply(self, model, assignments):
        """Ensure staff are only assigned to services they are available for."""
        for (flight_number, service_id, staff_id), var in assignments.items():
            flight = next(flight for flight in self.flights if flight.number == flight_number)
            flight_service = next(flight_service for flight_service in flight.flight_services if flight_service.id == service_id)
            staff = next(staff for staff in self.roster if staff.id == staff_id)

            # Get absolute service start and end times for the flight
            service_start, service_end = flight.get_service_time(flight_service.start, flight_service.end)

            # Check staff availability
            if not staff.is_available_for_service(service_start, service_end):
                logging.debug(f"Staff {staff_id} not available for service {service_id} at flight {flight.number}, setting var {var} to 0")
                model.Add(var == 0)