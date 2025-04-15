import logging
from .base_constraint import Constraint
from scheduler.models.base import ServiceType

class FixedServiceConstraint(Constraint):
    """
    Constraint to ensure:
    1. If a staff member is assigned to a Fixed (F) service on a flight, they cannot be assigned to any other service on the same flight.
    2. A staff member cannot be assigned to more than one Fixed service on the same flight.
    3. A staff member can only be assigned to the same Fixed service on different flights.
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
        logging.debug("Adding Fixed (F) service constraints...")

        # Step 1: Enforce Fixed constraints within the same flight
        for flight in self.flights:
            for staff in self.roster:
                # Collect assignment variables for Fixed (F) services
                Fixed_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type == ServiceType.FIXED
                ]

                # Collect assignment variables for non-Fixed services
                non_Fixed_vars = [
                    assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type != ServiceType.FIXED
                ]

                # Rule 1: A staff member cannot be assigned more than one Fixed service on the same flight
                model.Add(sum(Fixed_vars) <= 1)

                # Rule 2: If a Fixed service is assigned, no other services can be assigned on this flight
                for Fixed_var in Fixed_vars:
                    for non_Fixed_var in non_Fixed_vars:
                        model.Add(Fixed_var + non_Fixed_var <= 1)

        logging.debug("✅ Fixed (F) service constraints added for individual flights.")
       
        # Step 2: Track Fixed assignments across flights
        staff_Fixed_assignments = {staff.id: {} for staff in self.roster}

        for flight in self.flights:
            for staff in self.roster:
                for fs in flight.flight_services:
                    service = self.service_map[fs.id]
                    if service.type == ServiceType.FIXED:
                        var = assignments[(flight.number, fs.id, staff.id)]
                        if fs.id not in staff_Fixed_assignments[staff.id]:
                            staff_Fixed_assignments[staff.id][fs.id] = []
                        staff_Fixed_assignments[staff.id][fs.id].append(var)

        # Step 3: Enforce cross-flight consistency for Fixed services
        for staff_id, service_assignments in staff_Fixed_assignments.items():
            service_vars = [model.NewBoolVar(f"staff_{staff_id}_assigned_Fixed_{service_id}") 
                            for service_id in service_assignments]

            # Ensure staff is assigned at most ONE Fixed service across all flights
            model.Add(sum(service_vars) <= 1)

            for idx, (service_id, assignments) in enumerate(service_assignments.items()):
                # Ensure staff is assigned the same Fixed service across flights
                model.Add(sum(assignments) >= 1).OnlyEnforceIf(service_vars[idx])
                model.Add(sum(assignments) == 0).OnlyEnforceIf(service_vars[idx].Not())

                logging.debug(f"✅ Enforcing Fixed service consistency: Staff {staff_id} can only be assigned Fixed service {service_id} across flights.")

        logging.debug("✅ Fixed (F) service constraints added.")