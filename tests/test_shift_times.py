import pytest
from scheduler.core import Scheduler, Result
from scheduler.models import Service, Settings, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_single_shift_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            certifications=[1],
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
            flight_services=[FlightService(id=1, count=1, start="A-10", end="A+15")]
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

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    validate_schedule(schedule)

def test_multiple_shift_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            certifications=[1],
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
            arrival="10:30",
            departure="11:45",
            bay_number="A1",
            flight_services=[FlightService(id=1, count=1, start="A-10", end="A+15")]
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
    
    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
   
    schedule = scheduler.get_schedule()
    validate_schedule(schedule)