from enum import Enum

class ServiceType(Enum):
    FLIGHT_LEVEL = "F"
    COMMON_LEVEL = "C"
    MULTI_FLIGHT = "M"

class CertificationRequirement(Enum):
    ALL = "All"
    ANY = "Any"
