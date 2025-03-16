import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift

def test_staff_certification_check():
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
            certifications=[],
            shifts=[Shift(start="04:00", end="08:00")]  # Available but lacks certification
        ),
        Staff(
            id=2,
            certifications=[1],
            shifts=[Shift(start="06:00", end="10:00")]  # Certified but unavailable at "A-10" (05:20)
        ),
        Staff(
            id=3,
            certifications=[1],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()