from scheduler.core import Scheduler, Result
from scheduler.models import Bay, Flight, Service, Settings, Staff, FlightService, Shift, ServiceType, CertificationRequirement
from typing import List
import json

def load_bays(file_path: str) -> List[Bay]:
    with open(file_path, "r") as f:
        bays_data = json.load(f)

    return [Bay(number=bay["number"], travel_time=bay["travel_time"]) for bay in bays_data]

def load_flights(file_path: str) -> List[Flight]:
    with open(file_path) as f:
        flights_data = json.load(f)
    
    flights = []
    for flight in flights_data:
        flight_services = [FlightService(**fs) for fs in flight['flight_services']]
        flights.append(Flight(**{**flight, 'flight_services': flight_services}))
    
    return flights

def load_services(file_path: str) -> List[Service]:
    with open(file_path) as f:
        services_data = json.load(f)

    services = []
    for service in services_data:
        services.append(Service(**{**service, 'type': ServiceType(service['type']), 'certification_requirement': CertificationRequirement(service['certification_requirement'])}))
    
    print(f"SERVICES: {services}")
    return services

def load_roster(file_path: str) -> List[Staff]:
    with open(file_path) as f:
        roster_data = json.load(f)

    roster = []
    for staff in roster_data:
        shifts = [Shift(**shift) for shift in staff['shifts']]
        roster.append(Staff(**{**staff, 'shifts': shifts}))

    return roster

def run():
    bays = load_bays('data/bays.json')
    flights = load_flights('data/flights.json')
    services = load_services('data/services.json')
    roster = load_roster('data/roster.json')
    settings = Settings()

    print(f"BAYS: {bays}")
    scheduler = Scheduler(services, flights, roster, bays, settings)
    solution = scheduler.run()

    if solution == Result.FOUND:
        schedule = scheduler.get_schedule()
        schedule.display()

if __name__ == "__main__":
    run()