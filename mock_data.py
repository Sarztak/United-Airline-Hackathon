import pandas as pd

 
flight_schedule_df = pd.DataFrame([
    {
        "flight_id": "UA123",
        "origin": "ORD",
        "destination": "SFO",
        "sched_dep": "2024-08-10 08:00",
        "sched_arr": "2024-08-10 11:00",
        "aircraft_type": "B737",
        "delay_minutes": 21,  # 3.5 hr delay
        "status": "delayed",
        "gate": "C5",
        "remarks": "ground stop"
    },
    {
        "flight_id": "UA456",
        "origin": "SFO",
        "destination": "DEN",
        "sched_dep": "2024-08-10 12:00",
        "sched_arr": "2024-08-10 14:00",
        "aircraft_type": "B737",
        "delay_minutes": 0,
        "status": "ontime",
        "gate": "B12",
        "remarks": ""
    }
])

#  Crew Roster 
crew_roster_df = pd.DataFrame([
    {
        "crew_id": "C001",
        "name": "Jane Doe",
        "role": "captain",
        "base": "ORD",
        "qualified_aircraft": "B737",
        "assigned_flight_id": "UA123",
        "duty_start": "2024-08-10 07:00",
        "duty_end": "2024-08-10 15:00",
        "rest_until": "2024-08-10 23:00",
        "status": "active"
    },
    {
        "crew_id": "C002",
        "name": "John Roe",
        "role": "FO",
        "base": "ORD",
        "qualified_aircraft": "B737",
        "assigned_flight_id": "UA123",
        "duty_start": "2024-08-10 07:00",
        "duty_end": "2024-08-10 15:00",
        "rest_until": "2024-08-10 23:00",
        "status": "active"
    },
    {
        "crew_id": "C010",
        "name": "Sam Lee",
        "role": "FO",
        "base": "SFO",
        "qualified_aircraft": "B737",
        "assigned_flight_id": None,
        "duty_start": None,
        "duty_end": None,
        "rest_until": "2024-08-10 06:00",
        "status": "active"
    },
    {
        "crew_id": "C011",
        "name": "Alex Kim",
        "role": "FO",
        "base": "DEN",
        "qualified_aircraft": "B737",
        "assigned_flight_id": None,
        "duty_start": None,
        "duty_end": None,
        "rest_until": "2024-08-10 04:00",
        "status": "active"
    }
])

#  Hotel Inventory 
hotel_inventory_df = pd.DataFrame([
    {
        "hotel_id": "H001",
        "name": "ORD Airport Hotel",
        "location": "ORD",
        "capacity": 200,
        "available_rooms": 0
    },
    {
        "hotel_id": "H002",
        "name": "ORD Downtown Inn",
        "location": "ORD",
        "capacity": 150,
        "available_rooms": 10
    },
    {
        "hotel_id": "H003",
        "name": "SFO Airport Hotel",
        "location": "SFO",
        "capacity": 100,
        "available_rooms": 5
    },
    {
        "hotel_id": "H004",
        "name": "DEN Airport Hotel",
        "location": "DEN",
        "capacity": 120,
        "available_rooms": 8
    }
])

#  Repositioning Flights 
repositioning_flights_df = pd.DataFrame([
    {
        "flight_id": "UA9001",
        "origin": "DEN",
        "destination": "SFO",
        "sched_dep": "2024-08-10 10:00",
        "sched_arr": "2024-08-10 12:00",
        "seats_available": True
    },
    {
        "flight_id": "UA9002",
        "origin": "DEN",
        "destination": "ORD",
        "sched_dep": "2024-08-10 11:00",
        "sched_arr": "2024-08-10 13:00",
        "seats_available": False
    },
    {
        "flight_id": "UA9003",
        "origin": "SFO",
        "destination": "ORD",
        "sched_dep": "2024-08-10 09:00",
        "sched_arr": "2024-08-10 15:00",
        "seats_available": True
    }
])