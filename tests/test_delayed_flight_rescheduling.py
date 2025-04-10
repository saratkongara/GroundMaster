import pytest
from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Service, ServiceType, Flight, FlightService, Staff, Shift, CertificationRequirement
from tests.utils import validate_schedule

def test_rescheduling_for_delayed_flight():
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
            name="Refueling",
            certifications=[3,4],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.COMMON_LEVEL,
            exclude_services=[],
            cross_utilization_limit=0
        ),
        Service(
            id=3,
            name="Toilet Cleaning",
            certifications=[1],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[],
            cross_utilization_limit=2
        ),
        Service(
            id=4,
            name="Water Cart Service",
            certifications=[2],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[],
            cross_utilization_limit=2
        ),
        Service(
            id=5,
            name="Baggage Loading",
            certifications=[5,6],
            certification_requirement=CertificationRequirement.ALL,
            type=ServiceType.FLIGHT_LEVEL,
            exclude_services=[3,4],
            cross_utilization_limit=1
        )
    ]
    
    flights = [
        Flight(
            number="DL101",
            arrival="05:30",
            departure="06:45",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL104",
            arrival="7:00",
            departure="8:15",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL107",
            arrival="09:30",
            departure="10:45",
            flight_services=[FlightService(id=1, count=1, start="A", end="D"),FlightService(id=2, count=1, start="A+5", end="D-15"),FlightService(id=3, count=1, start="A-10", end="A+15"),FlightService(id=4, count=1, start="A-10", end="A+10"),FlightService(id=5, count=1, start="A+10", end="D-30")]
        ),
        Flight(
            number="DL109",
            arrival="10:45",
            departure="12:00",
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

    scheduler = Scheduler(services, flights, staff)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    schedule.display()

    #assert len(schedule.allocations) == 2, "Should have 2 schedules"
    validate_schedule(schedule)

    # Assume DL107 is delayed by 30, notification received at 9:00 AM
    allocation_plan = scheduler.get_allocation_plan()
    allocation_plan.remove_flight("DL107")

    # Remove the flights from the past and change the arrival and departure time of the delayed flight
    flights = flights[2:]
    flights[0].arrival = "10:00"
    flights[0].departure = "11:15"

    # Do incremental scheduling passing the hints from the previously generated schedule
    scheduler = Scheduler(services, flights, staff, allocation_plan)
    solution = scheduler.run()

    assert solution == Result.FOUND, "Scheduler should find a solution"

    schedule = scheduler.get_schedule()
    schedule.display()