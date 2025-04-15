import json
from typing import List, Dict
from scheduler.models import Flight, Service, Staff
from scheduler.models import Schedule, FlightAllocation, ServiceAllocation, StaffInfo

class AllocationPlan:
    def __init__(self, flights: List[Flight], service_map: Dict[int, Service], staff_map: Dict[int, Staff]):
        self.allocations = {}
        self.flight_map = {f.number: f for f in flights}
        self.service_map = service_map
        self.staff_map = staff_map

    def add_allocation(self, flight_number: str, service_id: int, staff_id: int, value: bool):       
        # Initialize flight_number if not present
        if flight_number not in self.allocations:
            self.allocations[flight_number] = {}
        
        # Initialize service_id if not present
        if service_id not in self.allocations[flight_number]:
            self.allocations[flight_number][service_id] = {}
        
        # Set the value for staff_id
        self.allocations[flight_number][service_id][staff_id] = value

    def serialize(self):
        return json.dumps(self.allocations, indent=4)
    
    def deserialize(self, json_string: str):
        """
        Deserialize a JSON string into an allocations dictionary.
        Converts string keys back to their original types (str, int, int).
        """
        # Load the JSON string into a dictionary
        allocations_json = json.loads(json_string)

        # Convert string keys back to their original types
        for flight_number, services in allocations_json.items():
            self.allocations[flight_number] = {}
            for service_id, staff in services.items():
                self.allocations[flight_number][int(service_id)] = {}
                for staff_id, value in staff.items():
                    self.allocations[flight_number][int(service_id)][int(staff_id)] = value

    def remove_flight(self, flight_number):
        if flight_number in self.allocations:
            del self.allocations[flight_number]

    def remove_service(self, service_id):
        for flight_number in self.allocations:
            if service_id in self.allocations[flight_number]:
                del self.allocations[flight_number][service_id]

    def remove_staff(self, staff_id):
        for flight_number in self.allocations:
            for service_id in self.allocations[flight_number]:
                if staff_id in self.allocations[flight_number][service_id]:
                    del self.allocations[flight_number][service_id][staff_id]

    def get_allocation(self, flight_number, service_id, staff_id):
        """
        Get the allocation value for the given flight number, service_id, and staff_id.
        Returns False if any key is missing in the nested dictionary.
        """
        return self.allocations.get(flight_number, {}).get(service_id, {}).get(staff_id, False)
    
    def get_schedule(self) -> Schedule:
        """Generates a complete Schedule from the allocation data."""
        schedule_allocations = []
        
        for flight_number, services in self.allocations.items():
            flight = self.flight_map.get(flight_number)
            if not flight:
                continue
                
            flight_allocation = FlightAllocation(
                flight_number=flight_number,
                arrival=flight.arrival,
                departure=flight.departure,
                services=[]
            )
            
            for service_id, staff_assignments in services.items():
                service = self.service_map.get(service_id)
                if not service:
                    continue
                
                flight_service = next(
                    (fs for fs in flight.flight_services if fs.id == service_id),
                    None
                )
                if not flight_service:
                    continue
                
                service_allocation = ServiceAllocation(
                    service_id=service.id,
                    service_name=service.name,
                    service_type=service.type.value,
                    staff_allocation=[
                        StaffInfo(staff_id=staff_id, staff_name=self._get_staff_name(staff_id))
                        for staff_id, assigned in staff_assignments.items()
                        if assigned
                    ],
                    required_staff_count=flight_service.count
                )
                
                flight_allocation.services.append(service_allocation)
            
            schedule_allocations.append(flight_allocation)
        
        return Schedule(allocations=schedule_allocations)
    
    def _get_staff_name(self, staff_id: int) -> str:
        """Helper to get staff name or return default if not found"""
        staff = self.staff_map.get(staff_id)
        return staff.name if staff else f"Unknown Staff ({staff_id})"