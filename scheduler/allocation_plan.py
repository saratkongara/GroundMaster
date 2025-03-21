import json

class AllocationPlan:
    def __init__(self):
        self.allocations = {}

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
        Returns None if any key is missing in the nested dictionary.
        """
        return self.allocations.get(flight_number, {}).get(service_id, {}).get(staff_id, None)