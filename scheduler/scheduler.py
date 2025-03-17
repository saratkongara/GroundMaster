import logging
from ortools.sat.python import cp_model
from .result import Result
from .models import Flight, Service, Staff, ServiceType
from .models import Schedule, FlightAllocation, FlightServiceAssignment, StaffAssignment
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class Scheduler:
    def __init__(self, services: List[Service], flights: List[Flight], roster: List[Staff]):
        self.services = services
        self.flights = flights
        self.roster = roster
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.assignments = {}

        # Precompute lookup maps
        self.flight_map = {flight.number: flight for flight in self.flights}
        self.staff_map = {staff.id: staff for staff in self.roster}
        self.service_map = {service.id: service for service in services}

    def solve(self):
        """Solve the staff allocation optimization problem."""
        logging.info("Starting to solve the allocation problem...")
        self.create_variables()

        self.add_constraints()
        self.add_staff_count_constraints()
        self.add_flight_level_service_constraints()
        self.add_common_level_service_constraints()
        self.add_multiflight_service_constraints()

        self.maximize_service_assignments()

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


    def add_constraints(self):
        self.add_certification_constraints()
        self.add_availability_constraints()

    def add_certification_constraints(self):
        """Add certification constraints. If the staff does not have all the certifications required for a service, then set the assignment decision variable to 0"""
        for (_, service_id, staff_id), var in self.assignments.items():
            service = next(service for service in self.services if service.id == service_id)
            staff = next(staff for staff in self.roster if staff.id == staff_id)
            
            if not all(cert in staff.certifications for cert in service.certifications):
                logging.debug(f"Staff {staff_id} not certified for service {service_id}, setting var {var} to 0")
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
        Ensure that staff can take multiple FlightLevel (F) services on the same flight 
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
        """Ensure that staff assigned to a Common Level (C) service cannot be assigned to any other service on the same flight."""
        logging.debug("Adding Common Level (C) service constraints...")

        for flight in self.flights:
            flight_services = flight.flight_services  # List of flight service assignments

            for staff in self.roster:
                assigned_services = {
                    fs.id: self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight_services
                }

                # Identify the Common Level (C) services
                common_level_vars = [
                    assigned_services[fs.id]
                    for fs in flight_services
                    if self.service_map[fs.id].type == ServiceType.COMMON_LEVEL
                ]

                if common_level_vars:
                    # Indicator variable: is staff assigned to at least one Common Level service?
                    is_assigned_common = self.model.NewBoolVar(f"staff_{staff.id}_common_level_flight_{flight.number}")

                    # Enforce the common level assignment logic
                    self.model.Add(sum(common_level_vars) == 1).OnlyEnforceIf(is_assigned_common)
                    self.model.Add(sum(common_level_vars) == 0).OnlyEnforceIf(is_assigned_common.Not())

                    # If assigned a Common Level service, no other services should be assigned
                    self.model.Add(sum(assigned_services.values()) == 1).OnlyEnforceIf(is_assigned_common)

                    logging.debug(f"Adding Common Level constraint: Staff {staff.id} cannot be assigned multiple services on flight {flight.number}.")

    def add_multiflight_service_constraints(self):
        """Ensure that staff assigned a MultiFlight (M) service cannot take any other service on the same flight 
        and can only take the same MultiFlight service across multiple flights."""
        
        logging.debug("Adding MultiFlight (M) service constraints...")

        # Step 1: Enforce MultiFlight constraints within the same flight
        for flight in self.flights:
            flight_services = flight.flight_services  # List of flight service assignments

            for staff in self.roster:
                assigned_services = {
                    fs.id: self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight_services
                }

                # Identify the MultiFlight (M) services
                multiflight_vars = [
                    assigned_services[fs.id]
                    for fs in flight_services
                    if self.service_map[fs.id].type == ServiceType.MULTI_FLIGHT
                ]

                if multiflight_vars:
                    # Indicator variable: Is the staff assigned at least one MultiFlight service on this flight?
                    is_assigned_multiflight = self.model.NewBoolVar(f"staff_{staff.id}_multiflight_flight_{flight.number}")

                    # Enforce the MultiFlight assignment logic
                    self.model.Add(sum(multiflight_vars) == 1).OnlyEnforceIf(is_assigned_multiflight)
                    self.model.Add(sum(multiflight_vars) == 0).OnlyEnforceIf(is_assigned_multiflight.Not())

                    # If assigned a MultiFlight service, no other services should be assigned
                    self.model.Add(sum(assigned_services.values()) == 1).OnlyEnforceIf(is_assigned_multiflight)

                    logging.debug(f"MultiFlight constraint: Staff {staff.id} can only be assigned one MultiFlight service on flight {flight.number}.")

        # Step 2: Build MultiFlight assignments for cross-flight enforcement
        staff_multiflight_assignments = {
            staff.id: {} for staff in self.roster
        }

        for flight in self.flights:
            for staff in self.roster:
                flight_services = flight.flight_services
                assigned_services = {
                    fs.id: self.assignments[(flight.number, fs.id, staff.id)]
                    for fs in flight_services
                }
                
                for fs in flight_services:
                    service = self.service_map[fs.id]
                    if service.type == ServiceType.MULTI_FLIGHT:
                        if fs.id not in staff_multiflight_assignments[staff.id]:
                            staff_multiflight_assignments[staff.id][fs.id] = []
                        staff_multiflight_assignments[staff.id][fs.id].append(assigned_services[fs.id])

        # Step 3: Enforce cross-flight consistency for MultiFlight services
        for staff_id, service_assignments in staff_multiflight_assignments.items():
            service_vars = [self.model.NewBoolVar(f"staff_{staff_id}_assigned_multiflight_{service_id}") 
                            for service_id in service_assignments]

            # Ensure that staff can only be assigned **ONE** MultiFlight service across all flights
            self.model.Add(sum(service_vars) <= 1)

            for idx, (service_id, assignments) in enumerate(service_assignments.items()):
                # If a staff member is assigned this MultiFlight service on any flight, they must be assigned it on at least one flight
                self.model.Add(sum(assignments) >= 1).OnlyEnforceIf(service_vars[idx])
                self.model.Add(sum(assignments) == 0).OnlyEnforceIf(service_vars[idx].Not())

                logging.debug(f"Enforcing MultiFlight service consistency: "
                            f"Staff {staff_id} can only be assigned MultiFlight service {service_id} across flights.")

    def maximize_service_assignments(self):
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

    def generate_schedule(self) -> Schedule:
        """Generates a schedule based on solver results."""
        allocations: Dict[str, FlightAllocation] = {}

        for (flight_number, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):  # If the staff is assigned to the service
                flight = self.flight_map[flight_number]
                service = self.service_map[service_id]
                staff = self.staff_map[staff_id]

                # Create or get existing FlightAllocation
                if flight_number not in allocations:
                    allocations[flight_number] = FlightAllocation(
                        flight_number=flight.number,
                        arrival=flight.arrival,
                        departure=flight.departure,
                        services=[]
                    )

                flight_allocation = allocations[flight_number]

                # Find or create FlightServiceAssignment
                service_assignment = next(
                    (s for s in flight_allocation.services if s.service_id == service_id),
                    None
                )
                if not service_assignment:
                    service_assignment = FlightServiceAssignment(
                        service_id=service.id,
                        service_name=service.name,
                        assigned_staff=[]
                    )
                    flight_allocation.services.append(service_assignment)

                # Add staff assignment
                service_assignment.assigned_staff.append(StaffAssignment(
                    staff_id=staff.id,
                    staff_name=staff.name
                ))

        return Schedule(allocations=list(allocations.values()))

    def display_schedule(self, schedule: Schedule):
        """Displays the generated schedule flight-wise in a readable format."""
        print("\n=== Services Schedule ===\n")
        for allocation in schedule.allocations:
            print(f"Flight {allocation.flight_number} | Arrival: {allocation.arrival} | Departure: {allocation.departure}")
            print("-" * 60)
            for service in allocation.services:
                staff_names = ", ".join([s.staff_name for s in service.assigned_staff])
                print(f"  {service.service_name.ljust(25)} : {staff_names if staff_names else 'No staff assigned'}")
            print("\n")

    def get_results(self):
        """Extract assignment results."""
        results = []
        for (flight, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):
                logging.info(f"Assignment: Flight {flight}, Service {service_id}, Staff {staff_id}")
                results.append({"flight": flight, "service_id": service_id, "staff_id": staff_id})
        return results