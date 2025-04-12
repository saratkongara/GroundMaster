import logging
from ortools.sat.python import cp_model
from .result import Result
from scheduler.models import Flight, Service, Staff, ServiceType, Bay
from scheduler.models import Schedule, FlightAllocation, ServiceAllocation, StaffInfo
from scheduler.plans import AllocationPlan
from typing import Dict, List
from datetime import timedelta
from collections import defaultdict
from scheduler.constraints import AvailabilityConstraint, CertificationConstraint, StaffCountConstraint

# This class uses Google OR Tools to create a schedule for dynamic ground staff allocation to flights for different above and below the wing services
# The key entities are certificate, staff, service, flight. The roster has the list of staff members with their shifts and certifications.
# The services is a list of service objects with start and end times described relative to Arrival(A) and Departure(D) times of the flight
# The flights is a list of flight objects with number, arrival and departure times along with flight services
# The flight service is an object linking the flight to the service, it includes the flight number, service id and the number of resources need for this service on the flight

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class Scheduler:
    def __init__(self, services: List[Service], flights: List[Flight], roster: List[Staff], bays: List[Bay], hints: AllocationPlan = None):
        self.services = services
        self.flights = flights
        self.roster = roster
        self.bays = {bay.number: bay for bay in bays}
        self.hints = hints
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.assignments = {}
        self.overlap_tolerance_buffer = 15  # minutes

        # Precompute lookup maps
        self.flight_map = {flight.number: flight for flight in self.flights}
        self.staff_map = {staff.id: staff for staff in self.roster}
        self.service_map = {service.id: service for service in services}
        self.travel_time_map = {
            (a, b): self.bays[a].travel_time.get(b, 0)
            for a in self.bays 
            for b in self.bays
        }
        self.overlapping_flights_map = self.get_overlapping_flights_map()

        self.constraints = [
            AvailabilityConstraint(flights, roster),
            CertificationConstraint(services, roster),
            StaffCountConstraint(flights, roster)
        ]

    def get_overlapping_flights_map(self):
        """
        Builds a mapping of flights to their potentially overlapping subsequent flights,
        considering service time windows, bay travel times, and allowed overlap tolerance.
        
        Returns:
            Dict[str, List[str]]: Mapping from each flight number to a list of flight numbers
            that may overlap with it (considering travel time and buffer), where overlapping
            flights always occur later in the schedule.
            
        Methodology:
            1. Flights are sorted chronologically by arrival time
            2. For each flight A, we examine all subsequent flights B
            3. We calculate the minimum required gap between flights as:
            max(travel_time_between_bays - overlap_tolerance_buffer, 0)
            4. An overlap is identified if:
            flight_A's latest service end + required_gap > flight_B's earliest service start
        """
        logging.debug("Building flight overlap map considering service times and travel requirements...")

        # Sort flights chronologically to enable single-pass comparison
        sorted_flights = sorted(self.flights, key=lambda f: f.arrival_time)
        overlap_map = defaultdict(list)

        for i, flight_a in enumerate(sorted_flights):
            # Get non-MultiFlight services for flight_a
            a_services = [
                fs for fs in flight_a.flight_services
                if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
            ]
            
            # Determine the latest service end time on this flight
            # (or departure time if no non-MultiFlight services exist)
            a_services_end = (
                max(flight_a.get_service_time(fs.start, fs.end)[1] for fs in a_services)
                if a_services  # Only calculate max if non-MultiFlight services exist
                else flight_a.departure_time  # Fallback to flight departure time
            )

            # Only check future flights (j > i)
            for j in range(i + 1, len(sorted_flights)):
                flight_b = sorted_flights[j]
                
                # Get non-MultiFlight services for flight_b
                b_services = [
                    fs for fs in flight_b.flight_services
                    if self.service_map[fs.id].type != ServiceType.MULTI_FLIGHT
                ]
                
                # Determine the earliest service start time on the subsequent flight
                # (or arrival time if no non-MultiFlight services exist)
                b_services_start = (
                    min(flight_b.get_service_time(fs.start, fs.end)[0] for fs in b_services)
                    if b_services  # Only calculate min if non-MultiFlight services exist
                    else flight_b.arrival_time  # Fallback to flight arrival time
                )

                # Get required travel time between bays (0 if same bay)
                travel_time = self.travel_time_map.get(
                    (flight_a.bay_number, flight_b.bay_number), 0)
                
                # Calculate minimum required gap between flights:
                # If buffer > travel_time, negative gap becomes 0 (allows full overlap)
                required_gap = max(travel_time - self.overlap_tolerance_buffer, 0)
                
                # Check for temporal conflict
                if a_services_end + timedelta(minutes=required_gap) > b_services_start:
                    overlap_map[flight_a.number].append(flight_b.number)
                    logging.debug(
                        f"Overlap detected: Flight {flight_a.number} (ends {a_services_end.time()}) "
                        f"conflicts with Flight {flight_b.number} (starts {b_services_start.time()}) "
                        f"when accounting for {required_gap} min required gap "
                        f"(travel: {travel_time} min, buffer: {self.overlap_tolerance_buffer} min)"
                    )
                else:
                    # No overlap with flight_b, and since flights are sorted by arrival time,
                    # no subsequent flights can overlap with flight_a either
                    break  # Exit inner loop early

        return overlap_map

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
        # self.add_certification_constraints()
        # self.add_availability_constraints()
        # self.add_staff_count_constraints()
        for constraint in self.constraints:
            constraint.apply(self.model, self.assignments)

        self.add_flight_level_service_constraints()
        self.add_common_level_service_constraints()
        self.add_multiflight_service_constraints()
        self.add_flight_transition_constraints(self.overlap_tolerance_buffer)

    def add_flight_level_service_constraints(self):
        """
        Ensure that staff can take multiple FlightLevel (F) services (cross utilization) on the same flight 
        only if they do not conflict (based on excludes_services).
        """

        logging.debug("Adding FlightLevel (F) service constraints...")

        for flight in self.flights:
            # Get FlightLevel (F) services for this flight
            flight_level_services = [
                flight_service for flight_service in flight.flight_services 
                if self.service_map[flight_service.id].type == ServiceType.FLIGHT_LEVEL
            ]

            for staff in self.roster:
                # Collect assignment variables for all F services on this flight for a selected staff member
                assigned_services = {
                    flight_service.id: self.assignments[(flight.number, flight_service.id, staff.id)]
                    for flight_service in flight_level_services
                }

                # Apply conflict constraints based on exclude_services rule
                for flight_level_service_b in flight_level_services:
                    service_b = self.service_map[flight_level_service_b.id]

                    for flight_level_service_a in flight_level_services:
                        if flight_level_service_a.id in service_b.exclude_services:  # Corrected rule
                            var_a = assigned_services[flight_level_service_a.id]
                            var_b = assigned_services[flight_level_service_b.id]
                            logging.debug(f"Adding exclude services conflict constraint: {flight_level_service_a.id} excluded in {flight_level_service_b.id} for staff {staff.id} on flight {flight.number}")
                            self.model.Add(var_a + var_b <= 1)  # Prevent simultaneous assignment

                # Apply cross_utilization_limit constraints
                for flight_level_service in flight_level_services:
                    service = self.service_map[flight_level_service.id]
                    cross_utilization_limit = service.cross_utilization_limit

                # Collect all other FlightLevel services for this staff member on the same flight
                # which can potentially be assigned to this staff member along with the current service
                # This is done to ensure that the staff member does not exceed the cross_utilization_limit
                # for the current service
                # Exclude the current flight_level_service from the list
                # Also exclude any services that are in the exclude_services list of the current service
                # or services that exclude the current service
                other_service_vars = [
                    assigned_services[other_service.id]
                    for other_service in flight_level_services
                    if other_service.id != flight_level_service.id
                    and flight_level_service.id not in self.service_map[other_service.id].exclude_services
                    and other_service.id not in self.service_map[flight_level_service.id].exclude_services
                ]

                # Add constraint to ensure the staff member does not exceed the cross_utilization_limit
                if other_service_vars:
                    self.model.Add(
                        assigned_services[flight_level_service.id] + sum(other_service_vars) <= cross_utilization_limit
                    )
                    logging.debug(f"Adding cross utilization constraint: Staff {staff.id} on flight {flight.number} for service {flight_level_service.id} with limit {cross_utilization_limit}")

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

                # Rule 1: A staff member cannot be assigned to more than one Common Level service on the same flight
                self.model.Add(sum(common_level_vars) <= 1)

                # Rule 2: If any Common Level service is assigned, no other services can be assigned
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

                # Rule 1: A staff member cannot be assigned more than one MultiFlight service on the same flight
                self.model.Add(sum(multiflight_vars) <= 1)

                # Rule 2: If a MultiFlight service is assigned, no other services can be assigned on this flight
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

            # Ensure staff is assigned at most ONE MultiFlight service across all flights
            self.model.Add(sum(service_vars) <= 1)

            for idx, (service_id, assignments) in enumerate(service_assignments.items()):
                # Ensure staff is assigned the same MultiFlight service across flights
                self.model.Add(sum(assignments) >= 1).OnlyEnforceIf(service_vars[idx])
                self.model.Add(sum(assignments) == 0).OnlyEnforceIf(service_vars[idx].Not())

                logging.debug(f"✅ Enforcing MultiFlight service consistency: Staff {staff_id} can only be assigned MultiFlight service {service_id} across flights.")

        logging.debug("✅ MultiFlight (M) service constraints added.")

    def add_flight_transition_constraints(self, overlap_tolerance_buffer: int):
        """
        Add constraints to ensure that staff members cannot be assigned to overlapping flight services:
        1. Only checks flights marked as overlapping in overlapping_flights_map
        2. Skips service pairs where staff isn't available during the service times
        3. Skips service pairs where staff lacks required certifications
        """
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

                            if adjusted_a_end > b_start + timedelta(minutes=overlap_tolerance_buffer):
                                var_a = self.assignments.get((flight_a.number, service_a.id, staff.id))
                                var_b = self.assignments.get((flight_b.number, service_b.id, staff.id))
                                
                                self.model.Add(var_a + var_b <= 1)
                                logging.debug(
                                    f"Conflict: Staff {staff.id} cannot serve both "
                                    f"{service_a.id}@{flight_a.number}(ends {a_end.time()}+{travel_time}min) "
                                    f"and {service_b.id}@{flight_b.number}(starts {b_start.time()})"
                                )
                                    
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
                service_assignment = ServiceAllocation(
                    service_id=service.id,
                    service_name=service.name,
                    service_type=service.type.value,
                    staff_allocation=[],
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
                    service_assignment.staff_allocation.append(StaffInfo(
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