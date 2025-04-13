import logging
from .base_constraint import Constraint
from scheduler.models.base import ServiceType

class MultiFlightServiceConstraint(Constraint):
    """
    Constraint to ensure:
    1. If a staff member is assigned to a Multi Flight (M) service on a flight, they cannot be assigned to any other service on the same flight.
    2. A staff member cannot be assigned to more than one Multi Flight service on the same flight.
    3. A staff member can only be assigned to the same Multi Flight service on different flights.
    """
    def __init__(self, flights, roster, service_map):
        self.flights = flights
        self.roster = roster
        self.service_map = service_map

    def apply(self, model, assignments):
        """
        Ensure that a staff member is not assigned to multiple services across different flights at the same time.
        Steps to add the constraint
        ===========================
        1. Group assignment variables by staff member.
        2. For each staff member, check if they are assigned to multiple services at the same time.
        3. Add a constraint to the OR-Tools model ensuring that the sum of assigned services does not exceed 1.
        """
        logging.debug("Adding MultiFlight (M) service constraints...")

        # Step 1: Enforce MultiFlight constraints within the same flight
        for flight in self.flights:
            for staff in self.roster:
                # Collect assignment variables for MultiFlight (M) services
                multiflight_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type == ServiceType.MULTI_FLIGHT
                ]

                # Collect assignment variables for non-MultiFlight services
                non_multiflight_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
                ]

                # Rule 1: A staff member cannot be assigned more than one MultiFlight service on the same flight
                model.Add(sum(multiflight_vars) <= 1)

                # Rule 2: If a MultiFlight service is assigned, no other services can be assigned on this flight
                for multiflight_var in multiflight_vars:
                    for non_multiflight_var in non_multiflight_vars:
                        model.Add(multiflight_var + non_multiflight_var <= 1)

        logging.debug("✅ MultiFlight (M) service constraints added for individual flights.")
       
        # Step 2: Track MultiFlight assignments across flights
        staff_multiflight_assignments = {staff.id: {} for staff in self.roster}

        for flight in self.flights:
            for staff in self.roster:
                for fs in flight.flight_services:
                    service = self.service_map[fs.id]
                    if service.type == ServiceType.MULTI_FLIGHT:
                        var = assignments[(flight.number, fs.id, staff.id)]
                        if fs.id not in staff_multiflight_assignments[staff.id]:
                            staff_multiflight_assignments[staff.id][fs.id] = []
                        staff_multiflight_assignments[staff.id][fs.id].append(var)

        # Step 3: Enforce cross-flight consistency for MultiFlight services
        for staff_id, service_assignments in staff_multiflight_assignments.items():
            service_vars = [model.NewBoolVar(f"staff_{staff_id}_assigned_multiflight_{service_id}") 
                            for service_id in service_assignments]

            # Ensure staff is assigned at most ONE MultiFlight service across all flights
            model.Add(sum(service_vars) <= 1)

            for idx, (service_id, assignments) in enumerate(service_assignments.items()):
                # Ensure staff is assigned the same MultiFlight service across flights
                model.Add(sum(assignments) >= 1).OnlyEnforceIf(service_vars[idx])
                model.Add(sum(assignments) == 0).OnlyEnforceIf(service_vars[idx].Not())

                logging.debug(f"✅ Enforcing MultiFlight service consistency: Staff {staff_id} can only be assigned MultiFlight service {service_id} across flights.")

        logging.debug("✅ MultiFlight (M) service constraints added.")