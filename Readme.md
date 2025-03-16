## GroundMaster
Project for testing the feasibility of performing dynamic allocation of aviation ground staff to flight services using Google OR Tools.

This code is built using TDD approach to make sure all the requirements are satisified by the OR model and constraints implemented in the project.

## Running the tool
Clone the repo

```sh
    cd GroundMaster

    pip3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt

    python3 allocator.py
```

The direct dependencies which are installed are:
1. ortools
2. pytest

## Running the unit tests

```sh
    pytest
```

## Service classification

1. FlightLevel (F): These tasks are specific to a flight, and staff can handle multiple tasks on the same flight if they have the required certifications.

Eg: Toilet Cleaning, Water Cart Service, Baggage Loading, ULD Loading/Unloading, Baggage Unloading

2. CommonLevel (C): These tasks require the staff to dedicate themselves entirely to the task and not perform other services on the same flight.

Eg: 
Refueling (Requires specialized certification and full attention)
Team Lead On-Block (Leadership role that oversees all below-the-wing activities)

3. MultiFlight (M): These are specialized tasks which are performed by limited staff across multiple flights.

Eg: GPU Service (Since GPU operations can run in parallel across flights)

Based on this classification, we can infer the following rules for staff allocation:

### FlightLevel (F) Services:
Staff assigned to F services can be cross-utilized on the same flight for other F services if they have the necessary certifications and availability.

Example: A staff member handling Toilet Cleaning (F) could also perform Water Cart Service (F) or Baggage Loading (F) on the same flight if they are certified.

### CommonLevel (C) Services:
Staff assigned to C services cannot be assigned to any other service on the same flight.

Example: A Refueling staff member cannot also handle Baggage Loading or Toilet Cleaning on the same flight.

### MultiFlight (M) Services:
Staff assigned to M services can only perform the same M service across multiple flights.

Example: A staff member working on GPU Service (M) can only do GPU operations for multiple flights and cannot take up any other role. 

