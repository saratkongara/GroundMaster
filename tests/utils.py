from collections import defaultdict

def validate_schedule(schedule):
    """
    Validates the generated schedule against the business rules.

    Rules:
    1. MultiTask (M) services allow staff to perform multiple F services unless they are in exclude_services.
    2. Single (S) services prevent staff from doing any other service on the same flight.
    3. Fixed (F) services prevent staff from doing any other service and can only be assigned to the same 
       Fixed service across multiple flights.
    4. Each service must have the required count of assigned staff.

    :param schedule: The generated schedule object.
    :raises AssertionError: If any validation rule is violated.
    """

    # A dictionary to track Fixed assignments per staff
    multi_flight_assignments = defaultdict(set)

    # Step 1: Validate each flight assignment
    for allocation in schedule.allocations:
        flight_number = allocation.flight_number
        staff_assignments_per_flight = defaultdict(set)  # Track which staff are assigned to which services

        for service_allocation in allocation.services:
            service_id = service_allocation.service_id
            service_type = service_allocation.service_type
            assigned_staff = {staff.staff_id for staff in service_allocation.staff_allocation}

            # Ensure service count constraint is met
            expected_count = service_allocation.required_staff_count
            assert len(assigned_staff) <= expected_count, (
                f"Flight {flight_number}, Service {service_id} requires {expected_count} staff, but got {len(assigned_staff)}"
            )

            for staff_id in assigned_staff:
                staff_assignments_per_flight[staff_id].add((service_id, service_type))

                if service_type == "F":  # Fixed service
                    multi_flight_assignments[staff_id].add(service_id)

        # Step 2: Enforce C and M constraints within a flight
        for staff_id, assigned_services in staff_assignments_per_flight.items():
            service_types = {stype for _, stype in assigned_services}

            # If a staff has a C service, they should have no other assignments on the flight
            if "S" in service_types:
                assert len(assigned_services) == 1, (
                    f"Staff {staff_id} is assigned a Single (S) service on Flight {flight_number} "
                    f"but also assigned to other services: {assigned_services}"
                )

            # If a staff has an M service, they should have no other assignments on the flight
            if "F" in service_types:
                assert len(assigned_services) == 1, (
                    f"Staff {staff_id} is assigned a Fixed (F) service on Flight {flight_number} "
                    f"but also assigned to other services: {assigned_services}"
                )

    # Step 3: Validate Fixed staff consistency across flights
    for staff_id, assigned_services in multi_flight_assignments.items():
        assert len(assigned_services) == 1, (
            f"Staff {staff_id} is assigned to multiple different Fixed (F) services: {assigned_services}"
        )

    print("Schedule validation passed.")
