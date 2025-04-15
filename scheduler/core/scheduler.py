import logging
from ortools.sat.python import cp_model
from .result import Result
from scheduler.models import Flight, Service, Staff, Bay
from scheduler.models import Settings, Schedule, FlightAllocation, ServiceAllocation, StaffInfo
from scheduler.plans import AllocationPlan
from typing import Dict, List
from scheduler.constraints import AvailabilityConstraint, CertificationConstraint, StaffCountConstraint, MultiTaskServiceConstraint, SingleServiceConstraint, FixedServiceConstraint, FlightTransitionConstraint
from scheduler.services import OverlapDetectionService

# The Scheduler class is the main entry point for the scheduling process
# The Scheduler class is responsible for creating a schedule for dynamic ground staff allocation to flights
# It uses Google OR Tools to solve the optimization problem of assigning staff to flights based on their availability, certifications, and service requirements
# The class takes in a list of services, flights, staff members, and bays, and uses these to create a schedule
# The class also includes methods for creating decision variables, adding constraints, setting the objective function, and generating the final schedule
# The class also includes methods for getting the allocation plan and the final schedule

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class Scheduler:
    def __init__(self, services: List[Service], flights: List[Flight], roster: List[Staff], bays: List[Bay], settings: Settings, hints: AllocationPlan = None):
        self.services = services
        self.flights = flights
        self.roster = roster
        self.bays = {bay.number: bay for bay in bays}
        self.hints = hints
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.assignments = {}
        self.settings = settings

        # Precompute lookup maps
        self.flight_map = {flight.number: flight for flight in self.flights}
        self.staff_map = {staff.id: staff for staff in self.roster}
        self.service_map = {service.id: service for service in services}
        self.travel_time_map = {
            (a, b): self.bays[a].travel_time.get(b, self.settings.default_travel_time)
            for a in self.bays 
            for b in self.bays
        }

        self.overlap_detector = OverlapDetectionService(
            flights=flights,
            travel_time_map=self.travel_time_map,
            service_map=self.service_map,
            buffer_minutes=settings.overlap_tolerance_buffer
        )

        self.overlapping_flights_map = self.overlap_detector.detect_overlaps()

        self.constraints = [
            AvailabilityConstraint(flights, roster),
            CertificationConstraint(services, roster),
            StaffCountConstraint(flights, roster),
            MultiTaskServiceConstraint(flights, roster, self.service_map),
            SingleServiceConstraint(flights, roster, self.service_map),
            FixedServiceConstraint(flights, roster, self.service_map),
            FlightTransitionConstraint(
                flights, roster, self.service_map, self.flight_map,
                self.travel_time_map, self.overlapping_flights_map,
                self.settings.overlap_tolerance_buffer
            )
        ]

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
        allocation_plan = AllocationPlan(self.flights, self.service_map, self.staff_map)
        
        for (flight_number, service_id, staff_id), var in self.assignments.items():
           allocation_plan.add_allocation(flight_number, service_id, staff_id, bool(self.solver.Value(var)))

        return allocation_plan

    def get_results(self):
        """Extract assignment results."""
        results = []
        for (flight, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):
                logging.info(f"Assignment: Flight {flight}, Service {service_id}, Staff {staff_id}")
                results.append({"flight": flight, "service_id": service_id, "staff_id": staff_id})
        return results