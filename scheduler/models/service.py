from dataclasses import dataclass, field
from typing import List
from .base import ServiceType, CertificationRequirement

@dataclass
class Service:
    id: int
    name: str
    certifications: List[int]  # List of certification IDs
    certification_requirement: CertificationRequirement
    type: ServiceType
    cross_utilization_limit: int
    exclude_services: List[int] = field(default_factory=list)