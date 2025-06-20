# main.py (CLI-based simulation)

from agents.crew_assignment import handle_crew_assignment
from agents.ops_support import handle_ops_support
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

    crew_df = pd.DataFrame(crew_roster)
    flight_df = pd.DataFrame(flight_schedule)
    hotel_df = pd.DataFrame(hotel_inventory)
    reposition_df = pd.DataFrame(reposition_flights)

    print("\n🚨 Disruption Detected: UA123 delayed 3.5 hours at ORD\n")

    print("[1] Running Crew Assignment Agent...")
    crew_result = handle_crew_assignment(
        flight_id="UA123",
        crew_roster_df=crew_df,
        flight_schedule_df=flight_df,
        repositioning_flights_df=reposition_df,
        duty_rules=duty_rules
    )
    print("Status:", crew_result["status"])
    print("Message:", crew_result["message"])

    if crew_result.get("policy"):
        print("Escalation Policy:", crew_result["policy"]["title"])

    if crew_result["status"] in ["reassigned", "repositioning_initiated"]:
        print("\n[2] Running Ops Support Agent...")
        crew_id = crew_result.get("spare_used")
        origin = flight_df.loc[flight_df["flight_id"] == "UA123", "origin"].iloc[0]
        ops_result = handle_ops_support(crew_id, origin, hotel_df)

        print("Status:", ops_result["status"])
        print("Message:", ops_result["message"])

        if ops_result.get("policy"):
            print("Escalation Policy:", ops_result["policy"]["title"])

if __name__ == "__main__":
    simulate_disruption()
