from scheduler.scheduler import Scheduler
from scheduler.result import Result
from scheduler.models import Flight, Service, Staff, FlightService, Shift, ServiceType
import json

def load_flights(file_path):
    with open(file_path) as f:
        flights_data = json.load(f)
    
    flights = []
    for flight in flights_data:
        flight_services = [FlightService(**fs) for fs in flight['flight_services']]
        flights.append(Flight(**{**flight, 'flight_services': flight_services}))
    
    return flights

def load_services(file_path):
    with open(file_path) as f:
        services_data = json.load(f)

    services = []
    for service in services_data:
        services.append(Service(**{**service, 'type': ServiceType(service['type'])}))
    
    print(f"SERVICES: {services}")
    return services

def load_roster(file_path):
    with open(file_path) as f:
        roster_data = json.load(f)

    roster = []
    for staff in roster_data:
        shifts = [Shift(**shift) for shift in staff['shifts']]
        roster.append(Staff(**{**staff, 'shifts': shifts}))

    return roster

def run():
    flights = load_flights('data/flights.json')
    services = load_services('data/services.json')
    roster = load_roster('data/roster.json')

    scheduler = Scheduler(services, flights, roster)
    solution = scheduler.solve()

    if solution == Result.FOUND:
        schedule = scheduler.get_schedule()
        scheduler.display_schedule(schedule)

if __name__ == "__main__":
    run()