import pytest
from scheduler.core import Scheduler, Result
from scheduler.models import Service, Settings, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_service_count_requirement():
    services = [
        Service(
            id=1,
            name="Refueling",
            certifications=[3,4],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.COMMON_LEVEL,
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
            flight_services=[FlightService(id=1, count=2, start="A+5", end="D-15")]
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
            name="Mike Johnson",
            certifications=[3,4],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    validate_schedule(schedule)