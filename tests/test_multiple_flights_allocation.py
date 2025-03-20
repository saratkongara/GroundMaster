import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift
from tests.utils import validate_schedule

def test_all_service_types_assignment_across_multiple_flights():
    services = [
        Service(
            id=1,
            name="GPU Service",
            start="A",
            end="D",
            certifications=[7],
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[]
        ),
        Service(
            id=2,
            name="Refueling",
            start="A+5",
            end="D-15",
            certifications=[3,4],
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=3,
            name="Toilet Cleaning",
            start="A-10",
            end="A+15",
            certifications=[1],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=4,
            name="Water Cart Service",
            start="A-10",
            end="A+10",
            certifications=[2],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[]
        ),
        Service(
            id=5,
            name="Baggage Loading",
            start="A+10",
            end="D-30",
            certifications=[5,6],
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[3,4]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1),FlightService(id=2, count=1),FlightService(id=3, count=1),FlightService(id=4, count=1),FlightService(id=5, count=1)]
        ),
        Flight(
            number="DL104",
            arrival="7:00",
            departure="9:15",
            flight_services=[FlightService(id=1, count=1),FlightService(id=2, count=1),FlightService(id=3, count=1),FlightService(id=4, count=1),FlightService(id=5, count=1)]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[3,4,7],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1,2,5,6],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=3,
            name="Mike Johnson",
            certifications=[3,4,7],
            shifts=[Shift(start="05:00", end="9:30")]  # Certified and available
        ),
        Staff(
            id=4,
            name="Sarah Lee",
            certifications=[1,2,5,6],
            shifts=[Shift(start="05:00", end="09:30")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.generate_schedule()
    scheduler.display_schedule(schedule)

    assert len(schedule.allocations) == 2, "Should have 2 schedules"
    validate_schedule(schedule)
