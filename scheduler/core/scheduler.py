import logging
from ortools.sat.python import cp_model
from .result import Result
from scheduler.models import Flight, Service, Staff, ServiceType, Bay
from scheduler.models import Schedule, FlightAllocation, ServiceAllocation, StaffInfo
from scheduler.plans import AllocationPlan
from typing import Dict, List
from datetime import timedelta
from collections import defaultdict
from scheduler.constraints import AvailabilityConstraint, CertificationConstraint, StaffCountConstraint, FlightLevelServiceConstraint, CommonLevelServiceConstraint, MultiFlightServiceConstraint, FlightTransitionConstraint

# The Scheduler class is the main entry point for the scheduling process
# The Scheduler class is responsible for creating a schedule for dynamic ground staff allocation to flights
# It uses Google OR Tools to solve the optimization problem of assigning staff to flights based on their availability, certifications, and service requirements
# The class takes in a list of services, flights, staff members, and bays, and uses these to create a schedule
# The class also includes methods for creating decision variables, adding constraints, setting the objective function, and generating the final schedule
# The class also includes methods for getting the allocation plan and the final schedule

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
            StaffCountConstraint(flights, roster),
            FlightLevelServiceConstraint(flights, roster, self.service_map),
            CommonLevelServiceConstraint(flights, roster, self.service_map),
            MultiFlightServiceConstraint(flights, roster, self.service_map),
            FlightTransitionConstraint(
                flights, roster, self.service_map, self.flight_map,
                self.travel_time_map, self.overlapping_flights_map,
                self.overlap_tolerance_buffer
            )
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
        for constraint in self.constraints:
            constraint.apply(self.model, self.assignments)
                              
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