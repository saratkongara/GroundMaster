import logging
from .base_constraint import Constraint
from scheduler.models.base import ServiceType

class SingleServiceConstraint(Constraint):
    """
    Constraint to ensure:
    1. If a staff member is assigned to a Single (S) service on a flight, they cannot be assigned to any other service on the same flight.
    2. A staff member cannot be assigned to more than one Single service on the same flight.
    3. A staff member can be assigned to different Single services across flights.
    """
    def __init__(self, flights, roster, service_map):
        self.flights = flights
        self.roster = roster
        self.service_map = service_map

    def apply(self, model, assignments):
        """Ensure that:
        1. Staff cannot be assigned to >1 Single (S) service per flight
        2. If assigned to any C service, cannot be assigned to any other services
        """
        logging.debug("Adding Single (S) service constraints...")

        for flight in self.flights:
            for staff in self.roster:
                # Collect assignment variables
                common_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type == ServiceType.SINGLE
                ]
                
                other_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type != ServiceType.SINGLE
                ]

                if not common_vars:
                    continue

                # Rule 1: At most one Single service
                model.Add(sum(common_vars) <= 1)

                if not other_vars:
                    continue

                # Create indicator variable
                has_common = model.NewBoolVar(f'common_{flight.number}_{staff.id}')

                # Link indicator to sum of common assignments (correct approach)
                model.Add(sum(common_vars) == 1).OnlyEnforceIf(has_common)
                model.Add(sum(common_vars) == 0).OnlyEnforceIf(has_common.Not())

                # Rule 2: If any Single service, no other services
                model.Add(sum(other_vars) == 0).OnlyEnforceIf(has_common)

        logging.debug("✅ Single (S) service constraints added.")