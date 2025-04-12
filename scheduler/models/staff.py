from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from .shift import Shift
from .service import Service
from .base import CertificationRequirement

@dataclass
class Staff:
    id: int
    name: str
    certifications: List[int]  # List of certification IDs
    shifts: List[Shift]

    def is_available_for_service(self, service_start: datetime, service_end: datetime) -> bool:
        """
        Checks if the staff has at least one shift that fully covers the service duration.
        """
        for shift in self.shifts:
            shift_start = datetime.strptime(shift.start, "%H:%M")
            shift_end = datetime.strptime(shift.end, "%H:%M")

            if shift_start <= service_start and shift_end >= service_end:
                return True  # Found a shift that fully covers the service

        return False  # No shift covers the service time

    def can_perform_service(self, service: Service) -> bool:
        """
        Checks if staff meets certification requirements for a service.
        """
        if service.certification_requirement == CertificationRequirement.ALL:
            return all(cert in self.certifications for cert in service.certifications)
        elif service.certification_requirement == CertificationRequirement.ANY:
            return any(cert in self.certifications for cert in service.certifications)
        
        return False # Certification requirement not met