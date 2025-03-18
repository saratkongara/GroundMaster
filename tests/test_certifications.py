import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift

def test_single_certification_requirement():
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
            certifications=[],
            shifts=[Shift(start="04:00", end="08:00")]  # Available but lacks certification
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1],
            shifts=[Shift(start="06:00", end="10:00")]  # Certified but unavailable at "A-10" (05:20)
        ),
        Staff(
            id=3,
            name="Mike Johnson",
            certifications=[1],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()

def test_certification_priority_requirement():
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
            certifications=[],
            shifts=[Shift(start="04:00", end="08:00")]  # Available but lacks certification
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1],
            shifts=[Shift(start="05:00", end="8:00")]  # Certified and available with 1 certification
        ),
        Staff(
            id=3,
            name="Mike Johnson",
            certifications=[1, 2],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available with 2 certifications
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()

def test_multiple_certifications_requirement():
    services = [
        Service(
            id=1,
            name="Baggage Loading",
            start="A+10",
            end="D-30",
            certifications=[5,6],
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
            certifications=[5],
            shifts=[Shift(start="04:00", end="08:00")]  # Available with 1 missing certification
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1,5,6],
            shifts=[Shift(start="05:00", end="8:00")]  # Available with additional certifications
        ),
        Staff(
            id=3,
            name="Mike Johnson",
            certifications=[5,6],
            shifts=[Shift(start="05:00", end="09:00")]  # Available with exact certifications
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()