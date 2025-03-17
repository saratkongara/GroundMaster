import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift

def test_service_count_requirement():
    services = [
        Service(
            id=1,
            name="Refueling",
            start="A+5",
            end="D-15",
            certifications=[3,4],
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=2)]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[1,3,4],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[3,4],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        ),
        Staff(
            id=3,
            name="Mike Johnson"
            certifications=[3,4],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()
