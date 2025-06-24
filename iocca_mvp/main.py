# main.py (CLI-based simulation)

from agents.crew_assignment import handle_crew_assignment
from agents.ops_support import handle_ops_support
from agents.policy_agent_llm import llm_policy_reason
from orchestrator.orchestrator import Orchestrator
import pandas as pd

def simulate_disruption():
    print("\n📦 Loading simulated data...")

    crew_roster = [
        {"crew_id": "C001", "assigned_flight_id": "UA123", "duty_end": "2024-08-10 07:30", "status": "active", "base": "ORD"},
        {"crew_id": "C002", "assigned_flight_id": "UA123", "duty_end": "2024-08-10 07:45", "status": "active", "base": "ORD"},
        {"crew_id": "C010", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "SFO"},
        {"crew_id": "C011", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "DEN"}
    ]

    flight_schedule = [
        {"flight_id": "UA123", "origin": "ORD", "destination": "SFO", "scheduled_dep": "2024-08-10 10:30", "scheduled_arr": "2024-08-10 13:00"}
    ]

    hotel_inventory = [
        {"hotel_id": "H001", "location": "ORD", "name": "Runway Inn", "available_rooms": 0},
        {"hotel_id": "H002", "location": "SFO", "name": "Jetlag Suites", "available_rooms": 2}
    ]

    reposition_flights = [
        {"flight_id": "RP101", "origin": "DEN", "destination": "ORD", "sched_dep": "2024-08-10 08:30", "sched_arr": "2024-08-10 10:15", "seats_available": True},
        {"flight_id": "RP102", "origin": "SFO", "destination": "ORD", "sched_dep": "2024-08-10 09:00", "sched_arr": "2024-08-10 12:00", "seats_available": False}
    ]

    duty_rules = {"max_duty_hours": 8, "min_rest_hours": 10}

    print("\n🚨 Disruption Detected: UA123 delayed 3.5 hours at ORD\n")

    orchestrator = Orchestrator(
        crew_agent=handle_crew_assignment,
        ops_agent=handle_ops_support,
        policy_agent=llm_policy_reason
    )

    results = orchestrator.handle_disruption(
        crew_roster=crew_roster,
        flight_schedule=flight_schedule,
        hotel_inventory=hotel_inventory,
        reposition_flights=reposition_flights,
        duty_rules=duty_rules
    )

    print("\n===== Orchestration Results =====\n")
    for step in results["steps"]:
        for key, value in step.items():
            print(f"[{key.upper()}]")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(value)
            print()
    print(f"FINAL STATUS: {results['final_status']}")

if __name__ == "__main__":
    simulate_disruption()
