import logging
from .base_constraint import Constraint
from scheduler.models.base import ServiceType

class FlightLevelServiceConstraint(Constraint):
    """
    Constraint to ensure that the number of staff assigned to a service is within the specified limits.
    """
    def __init__(self, flights, roster, service_map):
        self.flights = flights
        self.roster = roster
        self.service_map = service_map

    def apply(self, model, assignments):
        """
        Ensure that staff can take multiple FlightLevel (F) services (cross utilization) on the same flight 
        only if they do not conflict (based on excludes_services and cross_utilization_limit).
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
                staff_service_assignment_vars = {
                    flight_service.id: assignments[(flight.number, flight_service.id, staff.id)]
                    for flight_service in flight_level_services
                }

                self._apply_exclude_services_constraint(model, flight_level_services, staff_service_assignment_vars, flight.number, staff.id)
                self._apply_cross_utilization_limit_constraint(model, flight_level_services, staff_service_assignment_vars, flight.number, staff.id)
                
    def _apply_exclude_services_constraint(self, model, flight_level_services, staff_service_assignment_vars, flight_number, staff_id):
        # Apply conflict constraints based on exclude_services rule
        for flight_level_service_a in flight_level_services:
            service_a = self.service_map[flight_level_service_a.id]

            for flight_level_service_b in flight_level_services:
                if flight_level_service_b.id in service_a.exclude_services:
                    var_a = staff_service_assignment_vars[flight_level_service_a.id]
                    var_b = staff_service_assignment_vars[flight_level_service_b.id]
                    
                    logging.debug(f"Adding exclude services conflict constraint: {flight_level_service_b.id} excluded in {flight_level_service_a.id} for staff {staff_id} on flight {flight_number}")
                    model.Add(var_a + var_b <= 1)  # Prevent simultaneous assignment

    def _apply_cross_utilization_limit_constraint(self, model, flight_level_services, staff_service_assignment_vars, flight_number, staff_id):
        # Collect all other FlightLevel services for this staff member on the same flight
        # which can potentially be assigned to this staff member along with the current service
        # This is done to ensure that the staff member does not exceed the cross_utilization_limit
        # for the current service
        # Exclude the current flight_level_service from the list
        # Also exclude any services that are in the exclude_services list of the current service
        # or services that exclude the current service
        
        for flight_level_service in flight_level_services:
            service = self.service_map[flight_level_service.id]
            cross_utilization_limit = service.cross_utilization_limit
   
        other_service_vars = [
            staff_service_assignment_vars[other_service.id]
            for other_service in flight_level_services
            if other_service.id != flight_level_service.id
            and flight_level_service.id not in self.service_map[other_service.id].exclude_services
            and other_service.id not in self.service_map[flight_level_service.id].exclude_services
        ]

        # Add constraint to ensure the staff member does not exceed the cross_utilization_limit
        if other_service_vars:
            model.Add(
                staff_service_assignment_vars[flight_level_service.id] + sum(other_service_vars) <= cross_utilization_limit
            )
            logging.debug(f"Adding cross utilization constraint: Staff {staff_id} on flight {flight_number} for service {flight_level_service.id} with limit {cross_utilization_limit}")