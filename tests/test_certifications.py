import pytest
from scheduler.core import Scheduler, Result
from scheduler.models import Service, Settings, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_single_certification_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            certifications=[1],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
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

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_allocation_plan().get_schedule()
    validate_schedule(schedule)

def test_certification_priority_requirement():
    services = [
        Service(
            id=1,
            name="Toilet Cleaning",
            certifications=[1],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
            exclude_services=[],
            cross_utilization_limit=2
        )
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
    
    bays = [
        Bay(number="A1", travel_time={"A2": 10, "B1": 5, "C1": 20}),
        Bay(number="A2", travel_time={"A1": 10, "B1": 15, "C1": 15}),
        Bay(number="B1", travel_time={"A1": 5, "A2": 15, "C1": 10}),
        Bay(number="C1", travel_time={"A1": 20, "A2": 15, "B1": 10}),
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

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
   
    schedule = scheduler.get_allocation_plan().get_schedule()
    validate_schedule(schedule)


def test_multiple_certification_requirement():
    services = [
        Service(
            id=1,
            name="Baggage Loading",
            certifications=[5,6],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
            exclude_services=[],
            cross_utilization_limit=1
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
            flight_services=[FlightService(id=1, count=1, start="A+10", end="D-30")]
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

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
      
    schedule = scheduler.get_allocation_plan().get_schedule()
    validate_schedule(schedule)
