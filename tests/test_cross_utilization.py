import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift
from tests.utils import validate_schedule

def test_cross_utilization_with_no_conflict_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            start="A-10",
            end="A+15",
            certifications=[1],
            type=ServiceType.FLIGHT_LEVEL,
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
            certifications=[1,2],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1,2],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)

def test_cross_utilization_with_exclude_services_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            start="A-10",
            end="A+15",
            certifications=[1],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=2,
            name="Water Cart Service",
            start="A-10",
            end="A+10",
            certifications=[2],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[1]
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
            certifications=[1,2],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1,2],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)