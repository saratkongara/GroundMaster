import logging
from ortools.sat.python import cp_model
from scheduler.result import Result
from scheduler.models import Flight, Service, Staff, ServiceType
from scheduler.models import Schedule, FlightAllocation, FlightServiceAssignment, StaffAssignment, CertificationRequirement
from scheduler.allocation_plan import AllocationPlan
from typing import Dict, List

# This class uses Google OR Tools to create a schedule for dynamic ground staff allocation to flights for different above and below the wing services
# The key entities are certificate, staff, service, flight. The roster has the list of staff members with their shifts and certifications.
# The services is a list of service objects with start and end times described relative to Arrival(A) and Departure(D) times of the flight
# The flights is a list of flight objects with number, arrival and departure times along with flight services
# The flight service is an object linking the flight to the service, it includes the flight number, service id and the number of resources need for this service on the flight

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class Scheduler:
    def __init__(self, services: List[Service], flights: List[Flight], roster: List[Staff], hints: AllocationPlan = None):
        self.services = services
        self.flights = flights
        self.roster = roster
        self.hints = hints
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.assignments = {}

        # Precompute lookup maps
        self.flight_map = {flight.number: flight for flight in self.flights}
        self.staff_map = {staff.id: staff for staff in self.roster}
        self.service_map = {service.id: service for service in services}

    def run(self):
        """Solve the staff allocation optimization problem."""
        logging.info("Starting to solve the allocation problem...")
        
        self.create_variables()
        self.add_constraints()
        self.set_objective()

        status = self.solver.Solve(self.model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logging.info("Solution found!")
            return Result.FOUND
        else:
            logging.warning("No feasible solution found.")
            return Result.NOT_FOUND
        
    def create_variables(self):
        """Create decision variables for flight-staff-service assignments."""
        logging.debug("Creating decision variables...")
        for flight in self.flights:
            for flight_service in flight.flight_services:
                for staff in self.roster:
                    key = (flight.number, flight_service.id, staff.id)
                    self.assignments[key] = self.model.NewBoolVar(f"assigned_{key}")
                    logging.debug(f"Created variable: assigned_{key}")

                    # Apply hints if provided
                    if self.hints:
                        hint = self.hints.get_allocation(flight.number, flight_service.id, staff.id)
                        if hint:
                            logging.debug(f"Applying hint: {hint} for key: {key}")
                            self.model.AddHint(self.assignments[key], 1)


    def add_constraints(self):
        self.add_certification_constraints()
        self.add_availability_constraints()
        self.add_staff_count_constraints()
        self.add_flight_level_service_constraints()
        self.add_common_level_service_constraints()
        self.add_multiflight_service_constraints()
        self.add_flight_transition_constraints()

    def add_certification_constraints(self):
        """Add certification constraints based on the certification requirement (ALL or ANY)."""
        for (_, service_id, staff_id), var in self.assignments.items():
            service = next(service for service in self.services if service.id == service_id)
            staff = next(staff for staff in self.roster if staff.id == staff_id)

            if service.certification_requirement == CertificationRequirement.ALL:
                # Staff must have all required certifications
                if not all(cert in staff.certifications for cert in service.certifications):
                    logging.debug(f"Staff {staff_id} does not meet ALL certifications for service {service_id}, setting var {var} to 0")
                    self.model.Add(var == 0)
            elif service.certification_requirement == CertificationRequirement.ANY:
                # Staff must have at least one of the required certifications
                if not any(cert in staff.certifications for cert in service.certifications):
                    logging.debug(f"Staff {staff_id} does not meet ANY certifications for service {service_id}, setting var {var} to 0")
                    self.model.Add(var == 0)

    def add_availability_constraints(self):
        """Ensure staff are only assigned to services they are available for."""
        for (flight_number, service_id, staff_id), var in self.assignments.items():
            flight = next(flight for flight in self.flights if flight.number == flight_number)
            service = next(service for service in self.services if service.id == service_id)
            staff = next(staff for staff in self.roster if staff.id == staff_id)

            # Get absolute service start and end times for the flight
            service_start, service_end = flight.get_service_time(service.start, service.end)

            # Check staff availability
            if not staff.is_available_for_service(service_start, service_end):
                logging.debug(f"Staff {staff_id} not available for service {service_id} at flight {flight.number}, setting var {var} to 0")
                self.model.Add(var == 0)
    
    def add_staff_count_constraints(self):
        """Ensure that at most count staff members are assigned to a service per flight."""

        """
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
                    self.assignments[(flight.number, service_id, staff.id)]
                    for staff in self.roster
                ]

                # Add constraint: Sum of assigned staff should not exceed max_count
                logging.debug(f"Adding staff count constraint for flight {flight.number}, service {service_id}: max {max_count}")
                self.model.Add(sum(service_assignments) <= max_count)

    def add_flight_level_service_constraints(self):
        """
        Ensure that staff can take multiple FlightLevel (F) services (cross utilization) on the same flight 
        only if they do not conflict (based on excludes_services).
        """

        logging.debug("Adding FlightLevel (F) service constraints...")

        for flight in self.flights:
            # Get FlightLevel (F) services for this flight
            flight_services = [
                flight_service for flight_service in flight.flight_services 
                if self.service_map[flight_service.id].type == ServiceType.FLIGHT_LEVEL
            ]

            for staff in self.roster:
                # Collect assignment variables for all F services on this flight for a selected staff member
                assigned_services = {
                    flight_service.id: self.assignments[(flight.number, flight_service.id, staff.id)]
                    for flight_service in flight_services
                }

                # Apply conflict constraints based on exclude_services rule
                for flight_service_b in flight_services:
                    service_b = self.service_map[flight_service_b.id]

                    for flight_service_a in flight_services:
                        if flight_service_a.id in service_b.exclude_services:  # Corrected rule
                            var_a = assigned_services[flight_service_a.id]
                            var_b = assigned_services[flight_service_b.id]
                            logging.debug(f"Adding conflict constraint: {flight_service_a.id} excluded in {flight_service_b.id} for staff {staff.id} on flight {flight.number}")
                            self.model.Add(var_a + var_b <= 1)  # Prevent simultaneous assignment

    def add_common_level_service_constraints(self):
        """Ensure that:
        1. If a staff member is assigned to a Common Level (C) service on a flight, they cannot be assigned to any other service on the same flight.
        2. A staff member cannot be assigned to more than one Common Level service on the same flight.
        """
        logging.debug("Adding Common Level (C) service constraints...")

        for flight in self.flights:
            for staff in self.roster:
                # Collect assignment variables for Common Level (C) services
                common_level_vars = [
                    self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type == ServiceType.COMMON_LEVEL
                ]

                # Collect assignment variables for non-Common Level services
                non_common_level_vars = [
                    self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type != ServiceType.COMMON_LEVEL
                ]

                # Rule 2: A staff member cannot be assigned to more than one Common Level service on the same flight
                self.model.Add(sum(common_level_vars) <= 1)

                # Rule 1: If any Common Level service is assigned, no other services can be assigned
                for common_var in common_level_vars:
                    for non_common_var in non_common_level_vars:
                        self.model.Add(common_var + non_common_var <= 1)

        logging.debug("✅ Common Level (C) service constraints added.")

    def add_multiflight_service_constraints(self):
        """Ensure staff assigned a MultiFlight (M) service:
        - Cannot take any other service on the same flight.
        - Can only take the same MultiFlight service across multiple flights.
        - Cannot be assigned multiple different MultiFlight services.
        """

        logging.debug("Adding MultiFlight (M) service constraints...")

        # Step 1: Enforce MultiFlight constraints within the same flight
        for flight in self.flights:
            for staff in self.roster:
                # Collect assignment variables for MultiFlight (M) services
                multiflight_vars = [
                    self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type == ServiceType.MULTI_FLIGHT
                ]

                # Collect assignment variables for non-MultiFlight services
                non_multiflight_vars = [
                    self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight.flight_services
                    if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
                ]

                # Rule 1: A staff member **cannot be assigned more than one MultiFlight service** on the same flight
                self.model.Add(sum(multiflight_vars) <= 1)

                # Rule 2: If a MultiFlight service is assigned, **no other services can be assigned** on this flight
                for multiflight_var in multiflight_vars:
                    for non_multiflight_var in non_multiflight_vars:
                        self.model.Add(multiflight_var + non_multiflight_var <= 1)

        logging.debug("✅ MultiFlight (M) service constraints added for individual flights.")
       
        # Step 2: Track MultiFlight assignments across flights
        staff_multiflight_assignments = {staff.id: {} for staff in self.roster}

        for flight in self.flights:
            for staff in self.roster:
                for fs in flight.flight_services:
                    service = self.service_map[fs.id]
                    if service.type == ServiceType.MULTI_FLIGHT:
                        var = self.assignments[(flight.number, fs.id, staff.id)]
                        if fs.id not in staff_multiflight_assignments[staff.id]:
                            staff_multiflight_assignments[staff.id][fs.id] = []
                        staff_multiflight_assignments[staff.id][fs.id].append(var)

        # Step 3: Enforce cross-flight consistency for MultiFlight services
        for staff_id, service_assignments in staff_multiflight_assignments.items():
            service_vars = [self.model.NewBoolVar(f"staff_{staff_id}_assigned_multiflight_{service_id}") 
                            for service_id in service_assignments]

            # 🚀 **Ensure staff is assigned at most ONE MultiFlight service across all flights**
            self.model.Add(sum(service_vars) <= 1)

            for idx, (service_id, assignments) in enumerate(service_assignments.items()):
                # 🚀 **Ensure staff is assigned the same MultiFlight service across flights**
                self.model.Add(sum(assignments) >= 1).OnlyEnforceIf(service_vars[idx])
                self.model.Add(sum(assignments) == 0).OnlyEnforceIf(service_vars[idx].Not())

                logging.debug(f"✅ Enforcing MultiFlight service consistency: Staff {staff_id} can only be assigned MultiFlight service {service_id} across flights.")

        logging.debug("✅ MultiFlight (M) service constraints added.")

    def add_flight_transition_constraints(self):
        """Ensure staff can complete a service on one flight before moving to the next flight."""
        logging.debug("Adding flight transition constraints...")

        for staff in self.roster:
            for flight1 in self.flights:
                for flight2 in self.flights:
                    if flight1.number == flight2.number:
                        continue  # Skip same flight

                    for flight_service1 in flight1.flight_services:
                        for flight_service2 in flight2.flight_services:
                            service1 = self.service_map[flight_service1.id]
                            service2 = self.service_map[flight_service2.id]

                            # Get absolute service times
                            service1_start, service1_end = flight1.get_service_time(service1.start, service1.end)
                            service2_start, service2_end = flight2.get_service_time(service2.start, service2.end)

                            # Log service times for debugging
                            # logging.debug(
                            #     f"Checking transition for staff {staff.id}: "
                            #     f"Flight {flight1.number} Service {service1.id} ({service1_start}-{service1_end}) vs "
                            #     f"Flight {flight2.number} Service {service2.id} ({service2_start}-{service2_end})"
                            # )

                            # Check for overlap
                            if service1_start < service2_end and service1_end > service2_start:
                                var1 = self.assignments[(flight1.number, service1.id, staff.id)]
                                var2 = self.assignments[(flight2.number, service2.id, staff.id)]
                                # logging.debug(
                                #     f"Conflict detected: Staff {staff.id} cannot be assigned to "
                                #     f"service {service2.id} on flight {flight2.number} before completing "
                                #     f"service {service1.id} on flight {flight1.number}"
                                # )
                                self.model.Add(var1 + var2 <= 1)

    def set_objective(self):
        # Prioritize staff with fewer certifications
        weighted_assignments = sum(
            var * (1 / max(len(staff.certifications), 1))  # Higher weight for fewer certifications
            for (_, _, staff_id), var in self.assignments.items()
            for staff in self.roster if staff.id == staff_id
        )

        # Ensure we maximize total service assignments as well
        total_assignments = sum(self.assignments.values())

        # Combine both objectives with a weight factor
        self.model.Maximize(weighted_assignments + total_assignments)

        # Maximize total assignments
        #self.model.Maximize(sum(self.assignments.values()))

    def get_allocation_plan(self) -> AllocationPlan:
        allocation_plan = AllocationPlan()
        
        for (flight_number, service_id, staff_id), var in self.assignments.items():
           allocation_plan.add_allocation(flight_number, service_id, staff_id, bool(self.solver.Value(var)))

        return allocation_plan

    def get_schedule(self) -> Schedule:
        """Generates a complete schedule including all services for all flights.
        If no staff is assigned to a service, it will still be included with an empty staff list.
        """
        allocations: Dict[str, FlightAllocation] = {}

        # Step 1: Iterate over all flights and services to initialize schedule
        for flight in self.flights:
            flight_allocation = FlightAllocation(
                flight_number=flight.number,
                arrival=flight.arrival,
                departure=flight.departure,
                services=[]
            )

            for flight_service in flight.flight_services:
                service = self.service_map[flight_service.id]

                # Create a FlightServiceAssignment with an empty staff list
                service_assignment = FlightServiceAssignment(
                    service_id=service.id,
                    service_name=service.name,
                    service_type=service.type.value,
                    assigned_staff=[],
                    required_staff_count=flight_service.count
                )

                flight_allocation.services.append(service_assignment)

            allocations[flight.number] = flight_allocation

        # Step 2: Iterate over assignments and populate assigned staff
        for (flight_number, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):  # If the staff is assigned to the service
                flight_allocation = allocations[flight_number]
                service_assignment = next(
                    (s for s in flight_allocation.services if s.service_id == service_id),
                    None
                )

                if service_assignment:
                    staff = self.staff_map[staff_id]
                    service_assignment.assigned_staff.append(StaffAssignment(
                        staff_id=staff.id,
                        staff_name=staff.name
                    ))

        return Schedule(allocations=list(allocations.values()))

    def get_results(self):
        """Extract assignment results."""
        results = []
        for (flight, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):
                logging.info(f"Assignment: Flight {flight}, Service {service_id}, Staff {staff_id}")
                results.append({"flight": flight, "service_id": service_id, "staff_id": staff_id})
        return results