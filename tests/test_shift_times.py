import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift
from tests.utils import validate_schedule

def test_single_shift_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            start="A-10",
            end="A+15",
            certifications=[1],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1)]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[1],
            shifts=[Shift(start="06:00", end="10:00")]  # Certified but unavailable at "A-10" (05:20)
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    validate_schedule(schedule)

def test_multiple_shift_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            start="A-10",
            end="A+15",
            certifications=[1],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="10:30",
            departure="11:45",
            flight_services=[FlightService(id=1, count=1)]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[1],
            shifts=[Shift(start="04:00", end="07:00"), Shift(start="10:00", end="11:00")]  # Certified and available in the second shift
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and unavailable
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
   
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)