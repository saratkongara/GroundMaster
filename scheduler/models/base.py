from enum import Enum

class ServiceType(Enum):
    MULTI_TASK = "M"
    SINGLE = "S"
    FIXED = "F"

class CertificationRequirement(Enum):
    ALL = "All"
    ANY = "Any"
