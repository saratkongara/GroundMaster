import logging
from .base_constraint import Constraint

class StaffCountConstraint(Constraint):
    """
    Constraint to ensure that the number of staff assigned to a service is within the specified limits.
    """
    def __init__(self, flights, roster):
        self.flights = flights
        self.roster = roster

    def apply(self, model, assignments):
        """
        Ensure that at most count staff members are assigned to a service per flight.
        Steps to add the constraint
        ===========================
        1. Group assignment variables by (flight, service), i.e., collect all BoolVars related to a particular service on a flight.
        2. Sum them up to ensure that the total number of assigned staff does not exceed the count limit.
        3. Add a constraint to the OR-Tools model ensuring that the sum does not exceed count.
        """
        for flight in self.flights:
            for flight_service in flight.flight_services:
                service_id = flight_service.id
                max_count = flight_service.count  # Max staff allowed for this service
                
                # Collect all variables related to this (flight, service)
                service_assignments = [
                    assignments[(flight.number, service_id, staff.id)]
                    for staff in self.roster
                ]

                # Add constraint: Sum of assigned staff should not exceed max_count
                logging.debug(f"Adding staff count constraint for flight {flight.number}, service {service_id}: max {max_count}")
                model.Add(sum(service_assignments) <= max_count)