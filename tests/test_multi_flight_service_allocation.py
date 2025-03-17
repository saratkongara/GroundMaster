import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift

def test_only_one_multi_flight_service_assignment():
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
            name="Pushback",
            start="D-10",
            end="D",
            certifications=[12],
            type=ServiceType.MULTI_FLIGHT,
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
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()

def test_same_multi_flight_service_assignment_across_flights():
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
            name="Pushback",
            start="D-10",
            end="D",
            certifications=[12],
            type=ServiceType.MULTI_FLIGHT,
            exclude_services=[]
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1), FlightService(id=2, count=1)]
        ),
        Flight(
            number="DL102",
            arrival="07:00",
            departure="08:45",
            flight_services=[FlightService(id=1, count=1), FlightService(id=2, count=1)]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="10:00")]  # Certified and available
        ),
        Staff(
            id=2,
            certifications=[7,12],
            shifts=[Shift(start="05:00", end="09:00")]  # Certified and available
        )
    ]

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.solve()

    assert solution == Result.FOUND, "Scheduler should find a solution"
    scheduler.get_results()
