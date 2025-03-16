import logging
from ortools.sat.python import cp_model
from .result import Result
from .models import Flight, Service, Staff, ServiceType
from typing import List

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

    def solve(self):
        """Solve the staff allocation optimization problem."""
        logging.info("Starting to solve the allocation problem...")
        self.create_variables()

        self.add_constraints()
        self.add_staff_count_constraints()
        self.add_flight_level_service_constraints()

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

        # Precompute service details lookup by service_id
        service_lookup = {service.id: service for service in self.services}

        for flight in self.flights:
            # Get FlightLevel (F) services for this flight
            flight_services = [
                flight_service for flight_service in flight.flight_services 
                if service_lookup[flight_service.id].type == ServiceType.FLIGHT_LEVEL
            ]

            for staff in self.roster:
                # Collect assignment variables for all F services on this flight for a selected staff member
                assigned_services = {
                    flight_service.id: self.assignments[(flight.number, flight_service.id, staff.id)]
                    for flight_service in flight_services
                }

                # Apply conflict constraints based on exclude_services rule
                for flight_service_b in flight_services:
                    service_b = service_lookup[flight_service_b.id]

                    for flight_service_a in flight_services:
                        if flight_service_a.id in service_b.exclude_services:  # Corrected rule
                            var_a = assigned_services[flight_service_a.id]
                            var_b = assigned_services[flight_service_b.id]
                            logging.debug(f"Adding conflict constraint: {flight_service_a.id} excluded in {flight_service_b.id} for staff {staff.id} on flight {flight.number}")
                            self.model.Add(var_a + var_b <= 1)  # Prevent simultaneous assignment


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

    def get_results(self):
        """Extract assignment results."""
        results = []
        for (flight, service_id, staff_id), var in self.assignments.items():
            if self.solver.Value(var):
                logging.info(f"Assignment: Flight {flight}, Service {service_id}, Staff {staff_id}")
                results.append({"flight": flight, "service_id": service_id, "staff_id": staff_id})
        return results