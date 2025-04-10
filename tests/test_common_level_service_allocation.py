import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift
from tests.utils import validate_schedule

def test_only_one_common_level_service_assignment():
    services = [
        Service(
            id=1,
            name="Refueling",
            start="A+5",
            end="D-15",
            certifications=[3,4],
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=2,
            name="Team Lead On-Block",
            start="A",
            end="D",
            certifications=[8,9],
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1), FlightService(id=2, count=1)]
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

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)

def test_no_other_service_is_assigned_when_common_level_service_is_assigned():
    services = [
        Service(
            id=1,
            name="Refueling",
            start="A+5",
            end="D-15",
            certifications=[3,4],
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=2,
            name="Water Cart Service",
            start="A-10",
            end="A+10",
            certifications=[2],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1), FlightService(id=2, count=1)]
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

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)