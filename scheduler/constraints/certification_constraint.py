import logging
from .base_constraint import Constraint

class CertificationConstraint(Constraint):
    """
    Constraint to ensure that service specific certifications are held by the staff.
    """
    def __init__(self, services, roster):
        self.services = services
        self.roster = roster
        
    def apply(self, model, assignments):
        for (_, service_id, staff_id), var in assignments.items():
            service = next(service for service in self.services if service.id == service_id)
            staff = next(staff for staff in self.roster if staff.id == staff_id)
            
            if not staff.can_perform_service(service):
                logging.debug(
                    f"Staff {staff_id} does not meet {service.certification_requirement.value} "
                    f"certifications for service {service_id}, setting var {var} to 0"
                )
                model.Add(var == 0)