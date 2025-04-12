import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_only_one_multi_flight_service_assignment():
    services = [
        Service(
            id=1,
            name="GPU Service",
            certifications=[7],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=2,
            name="Pushback",
            certifications=[12],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[],
            cross_utilization_limit=0
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
            flight_services=[FlightService(id=1, count=1, start="A", end="D"), FlightService(id=2, count=1, start="D-10", end="D")]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff, bays)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    schedule.display()

    assert len(schedule.assignments) == 1, "Should have 1 schedule"
    validate_schedule(schedule)

def test_same_multi_flight_service_assignment_across_flights():
    services = [
        Service(
            id=1,
            name="GPU Service",
            certifications=[7],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=2,
            name="Pushback",
            certifications=[12],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[],
            cross_utilization_limit=0
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
            flight_services=[FlightService(id=1, count=1, start="A", end="D"), FlightService(id=2, count=1, start="D-10", end="D")]
        ),
        Flight(
            number="DL102",
            arrival="07:00",
            departure="08:45",
            bay_number="A2",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"), FlightService(id=2, count=1, start="D-10", end="D")]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff, bays)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    
    schedule = scheduler.get_schedule()
    schedule.display()

    assert len(schedule.assignments) == 2, "Should have 2 schedules"
    validate_schedule(schedule)
