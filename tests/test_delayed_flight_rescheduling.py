import pytest
from scheduler.core import Scheduler, Result
from scheduler.models import Service, Settings, ServiceType, Bay, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_rescheduling_for_delayed_flight():
    services = [
        Service(
            id=1,
            name="GPU Service",
            certifications=[7],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.FIXED,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=2,
            name="Refueling",
            certifications=[3,4],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.SINGLE,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=3,
            name="Toilet Cleaning",
            certifications=[1],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
            exclude_services=[],
            cross_utilization_limit=2
        ),
        Service(
            id=4,
            name="Water Cart Service",
            certifications=[2],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
            exclude_services=[],
            cross_utilization_limit=2
        ),
        Service(
            id=5,
            name="Baggage Loading",
            certifications=[5,6],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.MULTI_TASK,
            exclude_services=[3,4],
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
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL104",
            arrival="7:00",
            departure="8:15",
            bay_number="A2",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL107",
            arrival="09:30",
            departure="10:45",
            bay_number="B1",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL109",
            arrival="10:45",
            departure="12:00",
            bay_number="C1",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        )
    ]
    
    staff = [
        Staff(
            id=1,
            name="John Doe",
            certifications=[3,4,7],
            shifts=[Shift(start="05:00", end="12:00")]  # Certified and available
        ),
        Staff(
            id=2,
            name="Jane Smith",
            certifications=[1,2,5,6],
            shifts=[Shift(start="05:00", end="12:00")]  # Certified and available
        ),
        Staff(
            id=3,
            name="Mike Johnson",
            certifications=[3,4,7],
            shifts=[Shift(start="05:00", end="12:30")]  # Certified and available
        ),
        Staff(
            id=4,
            name="Sarah Lee",
            certifications=[1,2,5,6],
            shifts=[Shift(start="05:00", end="12:30")]  # Certified and available
        )
    ]

    settings = Settings()
    scheduler = Scheduler(services, flights, staff, bays, settings)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    allocation_plan = scheduler.get_allocation_plan()
    schedule = allocation_plan.get_schedule()
    schedule.display()

    #assert len(schedule.allocations) == 2, "Should have 2 schedules"
    validate_schedule(schedule)

    # Assume DL107 is delayed by 30, notification received at 9:00 AM
    allocation_plan.remove_flight("DL107")

    # Remove the flights from the past and change the arrival and departure time of the delayed flight
    flights = flights[2:]
    flights[0].arrival = "10:00"
    flights[0].departure = "11:15"

    # Do incremental scheduling passing the hints from the previously generated schedule
    scheduler = Scheduler(services, flights, staff, bays, settings, allocation_plan)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_allocation_plan().get_schedule()
    schedule.display()