import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_only_one_common_level_service_assignment():
    services = [
        Service(
            id=1,
            name="Refueling",
            certifications=[3,4],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=2,
            name="Team Lead On-Block",
            certifications=[8,9],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[],
            cross_utilization_limit=0
        )
    ]
    
    bays = [
        Bay(number="A1", travel_time={"A2": 10, "B1": 5, "C1": 20}),
        Bay(number="A2", travel_time={"A1": 10, "B1": 15, "C1": 15}),
        Bay(number="B1", travel_time={"A1": 5, "A2": 15, "C1": 10}),
        Bay(number="C1", travel_time={"A1": 20, "A2": 15, "B1": 10}),
    ]

    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            bay_number="A1",
            flight_services=[FlightService(id=1, count=1, start="A+5", end="D-15"), FlightService(id=2, count=1, start="A", end="D")]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[3,4,8,9],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[3,4,8,9],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff, bays)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)

def test_no_other_service_is_assigned_when_common_level_service_is_assigned():
    services = [
        Service(
            id=1,
            name="Refueling",
            certifications=[3,4],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=2,
            name="Water Cart Service",
            certifications=[2],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[],
            cross_utilization_limit=2
        )
    ]
    
    bays = [
        Bay(number="A1", travel_time={"A2": 10, "B1": 5, "C1": 20}),
        Bay(number="A2", travel_time={"A1": 10, "B1": 15, "C1": 15}),
        Bay(number="B1", travel_time={"A1": 5, "A2": 15, "C1": 10}),
        Bay(number="C1", travel_time={"A1": 20, "A2": 15, "B1": 10}),
    ]

    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            bay_number="A1",
            flight_services=[FlightService(id=1, count=1, start="A+5", end="D-15"), FlightService(id=2, count=1, start="A-10", end="A+10")]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[2,3,4],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[2,3,4],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff, bays)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)