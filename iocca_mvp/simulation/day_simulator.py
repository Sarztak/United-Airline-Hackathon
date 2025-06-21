"""
Dynamic Day Simulation for Crew Operations
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from langchain_agents.crew_assignment_agent import CrewAssignmentAgent
from langchain_agents.ops_support_agent import OpsupportAgent
from utils.logger import get_agent_logger

logger = get_agent_logger("day_simulator")

class DaySimulator:
    """Simulates a full day of airline operations with real-time disruptions"""
    
    def __init__(self):
        self.crew_agent = CrewAssignmentAgent()
        self.ops_agent = OpsupportAgent()
        
        # Simulation state
        self.current_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        self.end_time = self.current_time + timedelta(hours=18)  # 6 AM to 12 AM
        self.events = []
        self.disruptions = []
        
        # Generate realistic daily schedule
        self.flight_schedule = self._generate_daily_schedule()
        self.crew_roster = self._generate_crew_roster()
        self.hotel_inventory = self._generate_hotel_inventory()
        self.repositioning_flights = self._generate_repositioning_flights()
        self.duty_rules = {"max_duty_hours": 8, "min_rest_hours": 10}
        
        # Set agent contexts
        self.crew_agent.set_context(
            self.crew_roster, self.flight_schedule, 
            self.repositioning_flights, self.duty_rules
        )
        self.ops_agent.set_context(self.hotel_inventory)
    
    def _generate_daily_schedule(self) -> List[Dict[str, Any]]:
        """Generate a realistic daily flight schedule"""
        flights = []
        flight_routes = [
            ("ORD", "LAX"), ("LAX", "ORD"), ("ORD", "DEN"), ("DEN", "ORD"),
            ("SFO", "SEA"), ("SEA", "SFO"), ("MIA", "JFK"), ("JFK", "MIA"),
            ("ATL", "DFW"), ("DFW", "ATL"), ("BOS", "IAD"), ("IAD", "BOS")
        ]
        
        base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        for i in range(24):  # 24 flights throughout the day
            origin, destination = random.choice(flight_routes)
            dep_time = base_time + timedelta(hours=random.uniform(0, 18))
            arr_time = dep_time + timedelta(hours=random.uniform(2, 6))
            
            flights.append({
                "flight_id": f"UA{1000 + i}",
                "origin": origin,
                "destination": destination,
                "scheduled_dep": dep_time.isoformat(),
                "scheduled_arr": arr_time.isoformat(),
                "status": "scheduled",
                "crew_assigned": True
            })
        
        return sorted(flights, key=lambda x: x["scheduled_dep"])
    
    def _generate_crew_roster(self) -> List[Dict[str, Any]]:
        """Generate crew roster for the day"""
        crew = []
        bases = ["ORD", "LAX", "DEN", "SFO", "SEA", "MIA", "JFK", "ATL", "DFW", "BOS", "IAD"]
        
        # Assigned crew
        for i, flight in enumerate(self.flight_schedule):
            crew.extend([
                {
                    "crew_id": f"C{100 + i*2}",
                    "assigned_flight_id": flight["flight_id"],
                    "duty_end": (datetime.fromisoformat(flight["scheduled_arr"]) + timedelta(hours=2)).isoformat(),
                    "status": "active",
                    "base": flight["origin"],
                    "role": "captain"
                },
                {
                    "crew_id": f"C{100 + i*2 + 1}",
                    "assigned_flight_id": flight["flight_id"],
                    "duty_end": (datetime.fromisoformat(flight["scheduled_arr"]) + timedelta(hours=2)).isoformat(),
                    "status": "active",
                    "base": flight["origin"],
                    "role": "first_officer"
                }
            ])
        
        # Spare crew
        for i, base in enumerate(bases):
            crew.extend([
                {
                    "crew_id": f"S{200 + i*2}",
                    "assigned_flight_id": None,
                    "duty_end": None,
                    "status": "active",
                    "base": base,
                    "role": "captain"
                },
                {
                    "crew_id": f"S{200 + i*2 + 1}",
                    "assigned_flight_id": None,
                    "duty_end": None,
                    "status": "active",
                    "base": base,
                    "role": "first_officer"
                }
            ])
        
        return crew
    
    def _generate_hotel_inventory(self) -> List[Dict[str, Any]]:
        """Generate hotel inventory"""
        hotels = []
        locations = ["ORD", "LAX", "DEN", "SFO", "SEA", "MIA", "JFK", "ATL", "DFW", "BOS", "IAD"]
        hotel_names = [
            "Airport Plaza", "Runway Inn", "Sky Harbor Hotel", "Terminal Suites", 
            "Crew Rest Lodge", "Aviation Center", "Jetway Hotel", "Concourse Inn"
        ]
        
        for i, location in enumerate(locations):
            for j in range(2):  # 2 hotels per location
                hotels.append({
                    "hotel_id": f"H{i*2 + j + 1:03d}",
                    "location": location,
                    "name": f"{random.choice(hotel_names)} {location}",
                    "available_rooms": random.randint(0, 8),  # Some will be full
                    "crew_rate": random.randint(80, 150)
                })
        
        return hotels
    
    def _generate_repositioning_flights(self) -> List[Dict[str, Any]]:
        """Generate repositioning flight options"""
        reposition_flights = []
        bases = ["ORD", "LAX", "DEN", "SFO", "SEA", "MIA", "JFK", "ATL", "DFW", "BOS", "IAD"]
        
        # Generate repositioning options between major bases
        for i, origin in enumerate(bases):
            for j, destination in enumerate(bases):
                if origin != destination and random.random() < 0.3:  # 30% chance of route
                    base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
                    dep_time = base_time + timedelta(hours=random.uniform(1, 16))
                    arr_time = dep_time + timedelta(hours=random.uniform(1.5, 5))
                    
                    reposition_flights.append({
                        "flight_id": f"RP{len(reposition_flights) + 1:03d}",
                        "origin": origin,
                        "destination": destination,
                        "sched_dep": dep_time.isoformat(),
                        "sched_arr": arr_time.isoformat(),
                        "seats_available": random.choice([True, False])
                    })
        
        return reposition_flights
    
    async def simulate_day(self, callback=None):
        """Run the full day simulation"""
        logger.info(f"Starting day simulation from {self.current_time} to {self.end_time}")
        
        # Generate planned disruptions
        self._generate_disruptions()
        
        hour_count = 0
        while self.current_time < self.end_time:
            hour_count += 1
            
            # Log current simulation time
            sim_event = {
                "type": "time_update",
                "sim_time": self.current_time.isoformat(),
                "real_time": datetime.now().isoformat(),
                "hour": hour_count,
                "message": f"Simulation Hour {hour_count}: {self.current_time.strftime('%H:%M')}"
            }
            
            if callback:
                await callback(sim_event)
            
            # Check for flights departing this hour
            current_hour_flights = self._get_current_hour_flights()
            
            # Check for disruptions this hour
            current_disruptions = self._get_current_hour_disruptions()
            
            # Process normal operations
            for flight in current_hour_flights:
                if not any(d["flight_id"] == flight["flight_id"] for d in current_disruptions):
                    event = {
                        "type": "normal_operation",
                        "flight_id": flight["flight_id"],
                        "origin": flight["origin"],
                        "destination": flight["destination"],
                        "status": "departed_on_time",
                        "sim_time": self.current_time.isoformat()
                    }
                    if callback:
                        await callback(event)
            
            # Process disruptions
            for disruption in current_disruptions:
                await self._handle_disruption(disruption, callback)
            
            # Advance time by 1 hour
            self.current_time += timedelta(hours=1)
            
            # Wait 10 seconds (representing 1 hour)
            await asyncio.sleep(10)
        
        # Simulation complete
        completion_event = {
            "type": "simulation_complete",
            "message": "Day simulation completed successfully",
            "total_disruptions": len(self.disruptions),
            "sim_time": self.current_time.isoformat()
        }
        
        if callback:
            await callback(completion_event)
    
    def _generate_disruptions(self):
        """Generate realistic disruptions throughout the day"""
        disruption_types = [
            {"type": "weather", "probability": 0.2, "delay_range": (60, 240)},
            {"type": "maintenance", "probability": 0.15, "delay_range": (90, 360)},
            {"type": "crew_timeout", "probability": 0.1, "delay_range": (120, 480)},
            {"type": "atc_delay", "probability": 0.25, "delay_range": (30, 120)}
        ]
        
        for flight in self.flight_schedule:
            # 30% chance of any disruption per flight
            if random.random() < 0.3:
                disruption_type = random.choices(
                    disruption_types,
                    weights=[d["probability"] for d in disruption_types]
                )[0]
                
                delay_minutes = random.randint(*disruption_type["delay_range"])
                disruption_time = datetime.fromisoformat(flight["scheduled_dep"]) - timedelta(minutes=random.randint(30, 180))
                
                self.disruptions.append({
                    "flight_id": flight["flight_id"],
                    "type": disruption_type["type"],
                    "delay_minutes": delay_minutes,
                    "disruption_time": disruption_time,
                    "description": f"{disruption_type['type'].title()} causing {delay_minutes} minute delay"
                })
    
    def _get_current_hour_flights(self) -> List[Dict[str, Any]]:
        """Get flights scheduled for the current hour"""
        current_flights = []
        for flight in self.flight_schedule:
            flight_time = datetime.fromisoformat(flight["scheduled_dep"])
            if (flight_time.hour == self.current_time.hour and 
                flight_time.date() == self.current_time.date()):
                current_flights.append(flight)
        return current_flights
    
    def _get_current_hour_disruptions(self) -> List[Dict[str, Any]]:
        """Get disruptions occurring in the current hour"""
        current_disruptions = []
        for disruption in self.disruptions:
            if (disruption["disruption_time"].hour == self.current_time.hour and
                disruption["disruption_time"].date() == self.current_time.date()):
                current_disruptions.append(disruption)
        return current_disruptions
    
    async def _handle_disruption(self, disruption: Dict[str, Any], callback=None):
        """Handle a specific disruption with multi-agent coordination"""
        
        # Log disruption detected
        disruption_event = {
            "type": "disruption_detected",
            "flight_id": disruption["flight_id"],
            "disruption_type": disruption["type"],
            "delay_minutes": disruption["delay_minutes"],
            "description": disruption["description"],
            "sim_time": self.current_time.isoformat()
        }
        
        if callback:
            await callback(disruption_event)
        
        # Crew Assignment Agent analyzes the situation
        crew_response = self.crew_agent.handle_disruption(
            disruption["flight_id"], 
            disruption
        )
        
        crew_event = {
            "type": "crew_analysis",
            "flight_id": disruption["flight_id"],
            "agent": "crew_assignment",
            "reasoning": crew_response.get("reasoning", ""),
            "status": crew_response.get("status", "unknown"),
            "sim_time": self.current_time.isoformat()
        }
        
        if callback:
            await callback(crew_event)
        
        # If crew needs support, trigger Ops Support Agent
        if "hotel" in crew_response.get("reasoning", "").lower() or "accommodation" in crew_response.get("reasoning", "").lower():
            # Find affected crew
            flight = next((f for f in self.flight_schedule if f["flight_id"] == disruption["flight_id"]), None)
            if flight:
                affected_crew = [c for c in self.crew_roster if c["assigned_flight_id"] == disruption["flight_id"]]
                
                for crew_member in affected_crew[:1]:  # Handle first crew member as example
                    ops_response = self.ops_agent.handle_crew_support(
                        crew_member["crew_id"],
                        flight["origin"],
                        "accommodation"
                    )
                    
                    ops_event = {
                        "type": "ops_support",
                        "flight_id": disruption["flight_id"],
                        "crew_id": crew_member["crew_id"],
                        "agent": "ops_support",
                        "reasoning": ops_response.get("reasoning", ""),
                        "status": ops_response.get("status", "unknown"),
                        "sim_time": self.current_time.isoformat()
                    }
                    
                    if callback:
                        await callback(ops_event)
        
        # Resolution summary
        resolution_event = {
            "type": "disruption_resolved",
            "flight_id": disruption["flight_id"],
            "resolution": "Multi-agent coordination completed",
            "sim_time": self.current_time.isoformat()
        }
        
        if callback:
            await callback(resolution_event)