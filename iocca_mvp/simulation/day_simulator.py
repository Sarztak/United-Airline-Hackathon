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
        self.agent_responses = []  # Store detailed agent response data
        
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
        """Generate a strategic daily flight schedule for better showcases"""
        flights = []
        
        # Hub-based routes that will have good spare crew and repositioning options
        strategic_routes = [
            ("ORD", "LAX"), ("LAX", "ORD"), ("ORD", "DEN"), ("DEN", "ORD"),
            ("ORD", "ATL"), ("ATL", "ORD"), ("DEN", "LAX"), ("LAX", "DEN"),
            ("DEN", "SFO"), ("SFO", "DEN"), ("ATL", "MIA"), ("MIA", "ATL"),
            ("JFK", "BOS"), ("BOS", "JFK"), ("SEA", "SFO"), ("SFO", "SEA"),
            ("DFW", "ATL"), ("ATL", "DFW"), ("IAD", "BOS"), ("BOS", "IAD")
        ]
        
        base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        # Generate flights with realistic timing across the day
        for i in range(20):  # 20 strategic flights throughout the day
            origin, destination = random.choice(strategic_routes)
            
            # Distribute flights across different time periods
            if i < 6:  # Morning flights (6-10 AM)
                dep_time = base_time + timedelta(hours=random.uniform(0, 4))
            elif i < 12:  # Midday flights (10 AM - 2 PM)
                dep_time = base_time + timedelta(hours=random.uniform(4, 8))
            elif i < 18:  # Afternoon flights (2-6 PM)
                dep_time = base_time + timedelta(hours=random.uniform(8, 12))
            else:  # Evening flights (6-10 PM)
                dep_time = base_time + timedelta(hours=random.uniform(12, 16))
            
            # Calculate realistic flight times based on distance
            flight_duration = self._calculate_flight_duration(origin, destination)
            arr_time = dep_time + timedelta(hours=flight_duration)
            
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
    
    def _calculate_flight_duration(self, origin: str, destination: str) -> float:
        """Calculate realistic flight duration based on origin/destination"""
        # Rough flight durations in hours for common routes
        durations = {
            ("ORD", "LAX"): 4.5, ("LAX", "ORD"): 4.0,
            ("ORD", "DEN"): 2.5, ("DEN", "ORD"): 2.0,
            ("ORD", "ATL"): 2.0, ("ATL", "ORD"): 2.0,
            ("DEN", "LAX"): 2.5, ("LAX", "DEN"): 2.5,
            ("DEN", "SFO"): 2.5, ("SFO", "DEN"): 2.0,
            ("ATL", "MIA"): 2.0, ("MIA", "ATL"): 2.0,
            ("JFK", "BOS"): 1.5, ("BOS", "JFK"): 1.5,
            ("SEA", "SFO"): 2.0, ("SFO", "SEA"): 2.0,
            ("DFW", "ATL"): 2.0, ("ATL", "DFW"): 2.5,
            ("IAD", "BOS"): 1.5, ("BOS", "IAD"): 1.5
        }
        
        return durations.get((origin, destination), 3.0)  # Default 3 hours
    
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
        
        # Strategic spare crew placement - more at major hubs
        major_hubs = ["ORD", "DEN", "LAX", "ATL"]
        secondary_bases = ["SFO", "SEA", "MIA", "JFK", "DFW", "BOS", "IAD"]
        
        spare_crew_counter = 200
        
        # Extra spare crew at major hubs (3 captains, 3 first officers each)
        for hub in major_hubs:
            for crew_num in range(3):
                crew.extend([
                    {
                        "crew_id": f"S{spare_crew_counter}",
                        "assigned_flight_id": None,
                        "duty_end": None,
                        "status": "active",
                        "base": hub,
                        "role": "captain"
                    },
                    {
                        "crew_id": f"S{spare_crew_counter + 1}",
                        "assigned_flight_id": None,
                        "duty_end": None,
                        "status": "active",
                        "base": hub,
                        "role": "first_officer"
                    }
                ])
                spare_crew_counter += 2
        
        # Regular spare crew at secondary bases (1 captain, 1 first officer each)
        for base in secondary_bases:
            crew.extend([
                {
                    "crew_id": f"S{spare_crew_counter}",
                    "assigned_flight_id": None,
                    "duty_end": None,
                    "status": "active",
                    "base": base,
                    "role": "captain"
                },
                {
                    "crew_id": f"S{spare_crew_counter + 1}",
                    "assigned_flight_id": None,
                    "duty_end": None,
                    "status": "active",
                    "base": base,
                    "role": "first_officer"
                }
            ])
            spare_crew_counter += 2
        
        return crew
    
    def _generate_hotel_inventory(self) -> List[Dict[str, Any]]:
        """Generate strategic hotel inventory for better showcases"""
        hotels = []
        major_hubs = ["ORD", "LAX", "DEN", "SFO", "SEA", "MIA", "JFK", "ATL", "DFW", "BOS", "IAD"]
        hotel_names = [
            "Airport Plaza", "Runway Inn", "Sky Harbor Hotel", "Terminal Suites", 
            "Crew Rest Lodge", "Aviation Center", "Jetway Hotel", "Concourse Inn"
        ]
        
        hotel_counter = 1
        
        for location in major_hubs:
            # Each location gets 2-3 hotels with strategic availability
            num_hotels = random.choice([2, 3])
            
            for j in range(num_hotels):
                # Ensure at least one hotel per location has rooms available
                if j == 0:  # First hotel always has good availability
                    available_rooms = random.randint(4, 8)
                elif j == 1:  # Second hotel has moderate availability
                    available_rooms = random.randint(2, 6)
                else:  # Third hotel might be full or have few rooms
                    available_rooms = random.randint(0, 3)
                
                hotels.append({
                    "hotel_id": f"H{hotel_counter:03d}",
                    "location": location,
                    "name": f"{random.choice(hotel_names)} {location}",
                    "available_rooms": available_rooms,
                    "crew_rate": random.randint(89, 139)  # Crew rates
                })
                hotel_counter += 1
        
        return hotels
    
    def _generate_repositioning_flights(self) -> List[Dict[str, Any]]:
        """Generate strategic repositioning flight options for better showcases"""
        reposition_flights = []
        
        # Major hub-to-hub routes that are commonly needed
        major_routes = [
            ("ORD", "DEN"), ("DEN", "ORD"),
            ("ORD", "LAX"), ("LAX", "ORD"), 
            ("ORD", "ATL"), ("ATL", "ORD"),
            ("DEN", "LAX"), ("LAX", "DEN"),
            ("DEN", "SFO"), ("SFO", "DEN"),
            ("ATL", "MIA"), ("MIA", "ATL"),
            ("JFK", "BOS"), ("BOS", "JFK"),
            ("SEA", "SFO"), ("SFO", "SEA"),
            ("DFW", "ATL"), ("ATL", "DFW"),
            ("IAD", "BOS"), ("BOS", "IAD")
        ]
        
        base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        # Generate multiple flights per day for each major route (high success probability)
        for origin, destination in major_routes:
            # Morning repositioning (6-10 AM)
            dep_time = base_time + timedelta(hours=random.uniform(0.5, 4))
            arr_time = dep_time + timedelta(hours=random.uniform(1.5, 4))
            
            reposition_flights.append({
                "flight_id": f"RP{len(reposition_flights) + 1:03d}",
                "origin": origin,
                "destination": destination,
                "sched_dep": dep_time.isoformat(),
                "sched_arr": arr_time.isoformat(),
                "seats_available": True  # High availability for showcase
            })
            
            # Afternoon repositioning (12-4 PM)
            dep_time = base_time + timedelta(hours=random.uniform(6, 10))
            arr_time = dep_time + timedelta(hours=random.uniform(1.5, 4))
            
            reposition_flights.append({
                "flight_id": f"RP{len(reposition_flights) + 1:03d}",
                "origin": origin,
                "destination": destination,
                "sched_dep": dep_time.isoformat(),
                "sched_arr": arr_time.isoformat(),
                "seats_available": random.choice([True, True, False])  # 67% success rate
            })
        
        # Add some additional connecting routes
        additional_routes = [
            ("PHX", "LAX"), ("LAX", "PHX"),
            ("PDX", "SEA"), ("SEA", "PDX"),
            ("MSP", "ORD"), ("ORD", "MSP"),
            ("CLT", "ATL"), ("ATL", "CLT")
        ]
        
        for origin, destination in additional_routes:
            dep_time = base_time + timedelta(hours=random.uniform(2, 14))
            arr_time = dep_time + timedelta(hours=random.uniform(1.5, 3))
            
            reposition_flights.append({
                "flight_id": f"RP{len(reposition_flights) + 1:03d}",
                "origin": origin,
                "destination": destination,
                "sched_dep": dep_time.isoformat(),
                "sched_arr": arr_time.isoformat(),
                "seats_available": random.choice([True, False])  # 50% success rate
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
        
        # Create agent reasoning callback to stream to web UI
        async def agent_reasoning_callback(reasoning_event):
            """Stream agent reasoning steps to the web UI"""
            if callback:
                llm_event = {
                    "type": "llm_crew_reasoning",
                    "flight_id": disruption["flight_id"],
                    "sim_time": self.current_time.isoformat(),
                    "llm_event": reasoning_event
                }
                await callback(llm_event)
        
        # Crew Assignment Agent analyzes the situation with streaming
        crew_response = await self._run_crew_agent_with_streaming(
            disruption["flight_id"], 
            disruption,
            agent_reasoning_callback
        )
        
        # Extract structured response data
        crew_analysis = self._extract_crew_analysis_details(crew_response, disruption)
        
        crew_event = {
            "type": "crew_analysis",
            "flight_id": disruption["flight_id"],
            "agent": "crew_assignment",
            "reasoning": crew_response.get("reasoning", ""),
            "status": crew_response.get("status", "unknown"),
            "sim_time": self.current_time.isoformat(),
            "detailed_analysis": crew_analysis,
            "handoff_required": crew_response.get("handoff_required", False),
            "handoff_context": crew_response.get("handoff_context"),
            "response_time_ms": crew_analysis.get("response_time_ms", 0)
        }
        
        # Store detailed agent response
        self.agent_responses.append({
            "event_id": f"crew_{disruption['flight_id']}_{self.current_time.isoformat()}",
            "agent_type": "crew_assignment",
            "flight_id": disruption["flight_id"],
            "timestamp": self.current_time.isoformat(),
            "full_response": crew_response,
            "analysis": crew_analysis,
            "event_data": crew_event
        })
        
        if callback:
            await callback(crew_event)
        
        # If crew needs support, trigger Ops Support Agent with handoff context
        if crew_response.get("handoff_required", False) or "hotel" in crew_response.get("reasoning", "").lower() or "accommodation" in crew_response.get("reasoning", "").lower():
            # Find affected crew
            flight = next((f for f in self.flight_schedule if f["flight_id"] == disruption["flight_id"]), None)
            if flight:
                affected_crew = [c for c in self.crew_roster if c["assigned_flight_id"] == disruption["flight_id"]]
                
                for crew_member in affected_crew[:1]:  # Handle first crew member as example
                    # Use handoff context if available
                    handoff_context = crew_response.get("handoff_context", f"Crew {crew_member['crew_id']} requires accommodation due to duty time violation")
                    
                    # Create ops reasoning callback
                    async def ops_reasoning_callback(reasoning_event):
                        """Stream ops agent reasoning steps to the web UI"""
                        if callback:
                            llm_event = {
                                "type": "llm_ops_reasoning",
                                "flight_id": disruption["flight_id"],
                                "crew_ids": [crew_member["crew_id"]],
                                "sim_time": self.current_time.isoformat(),
                                "llm_event": reasoning_event
                            }
                            await callback(llm_event)
                    
                    ops_response = await self._run_ops_agent_with_streaming(
                        crew_member["crew_id"],
                        flight["origin"],
                        "accommodation",
                        handoff_context,
                        ops_reasoning_callback
                    )
                    
                    # Extract structured ops response data
                    ops_analysis = self._extract_ops_analysis_details(ops_response, crew_member, flight)
                    
                    ops_event = {
                        "type": "ops_support",
                        "flight_id": disruption["flight_id"],
                        "crew_id": crew_member["crew_id"],
                        "agent": "ops_support",
                        "reasoning": ops_response.get("reasoning", ""),
                        "status": ops_response.get("status", "unknown"),
                        "sim_time": self.current_time.isoformat(),
                        "detailed_analysis": ops_analysis,
                        "booking_confirmed": ops_response.get("booking_confirmed", False),
                        "hotel_details": ops_response.get("hotel_details"),
                        "response_time_ms": ops_analysis.get("response_time_ms", 0)
                    }
                    
                    # Store detailed ops agent response
                    self.agent_responses.append({
                        "event_id": f"ops_{crew_member['crew_id']}_{self.current_time.isoformat()}",
                        "agent_type": "ops_support",
                        "flight_id": disruption["flight_id"],
                        "crew_id": crew_member["crew_id"],
                        "timestamp": self.current_time.isoformat(),
                        "full_response": ops_response,
                        "analysis": ops_analysis,
                        "event_data": ops_event
                    })
                    
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
    
    def _extract_crew_analysis_details(self, crew_response: Dict[str, Any], disruption: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured details from crew assignment analysis"""
        reasoning = crew_response.get("reasoning", "")
        
        # Analyze the reasoning to extract key decisions
        analysis = {
            "disruption_type": disruption.get("type", "unknown"),
            "delay_minutes": disruption.get("delay_minutes", 0),
            "crew_legality_checked": "legal" in reasoning.lower() or "duty" in reasoning.lower(),
            "spare_crew_searched": "spare" in reasoning.lower() or "available" in reasoning.lower(),
            "repositioning_considered": "reposition" in reasoning.lower() or "flight" in reasoning.lower(),
            "accommodation_needed": "hotel" in reasoning.lower() or "accommodation" in reasoning.lower(),
            "tools_used": [],
            "decision_summary": "",
            "confidence_level": "medium",
            "response_time_ms": 0  # Would be measured in real implementation
        }
        
        # Extract tool usage patterns
        if "check_crew_legality" in reasoning:
            analysis["tools_used"].append("check_crew_legality")
        if "find_spare_crew" in reasoning:
            analysis["tools_used"].append("find_spare_crew")
        if "find_repositioning" in reasoning:
            analysis["tools_used"].append("find_repositioning")
        
        # Extract decision summary (first sentence or key conclusion)
        lines = reasoning.split('\n')
        for line in lines:
            if any(word in line.lower() for word in ["decision", "recommendation", "solution", "resolved"]):
                analysis["decision_summary"] = line.strip()[:100] + "..." if len(line) > 100 else line.strip()
                break
        
        if not analysis["decision_summary"]:
            analysis["decision_summary"] = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
        
        # Assess confidence based on response completeness
        if len(analysis["tools_used"]) >= 2 and analysis["decision_summary"]:
            analysis["confidence_level"] = "high"
        elif len(analysis["tools_used"]) == 1:
            analysis["confidence_level"] = "medium"
        else:
            analysis["confidence_level"] = "low"
        
        return analysis
    
    def _extract_ops_analysis_details(self, ops_response: Dict[str, Any], crew_member: Dict[str, Any], flight: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured details from operations support analysis"""
        reasoning = ops_response.get("reasoning", "")
        
        analysis = {
            "crew_id": crew_member.get("crew_id", "unknown"),
            "location": flight.get("origin", "unknown"),
            "support_type": "accommodation",
            "hotel_availability_checked": "hotel" in reasoning.lower() and "available" in reasoning.lower(),
            "booking_attempted": "book" in reasoning.lower() or "reservation" in reasoning.lower(),
            "cost_considered": "rate" in reasoning.lower() or "cost" in reasoning.lower() or "$" in reasoning,
            "tools_used": [],
            "booking_details": {},
            "decision_summary": "",
            "confidence_level": "medium",
            "response_time_ms": 0
        }
        
        # Extract tool usage patterns
        if "check_hotel_availability" in reasoning:
            analysis["tools_used"].append("check_hotel_availability")
        if "book_crew_hotel" in reasoning:
            analysis["tools_used"].append("book_crew_hotel")
        
        # Extract booking details if confirmed
        if ops_response.get("booking_confirmed", False):
            hotel_details = ops_response.get("hotel_details", {})
            analysis["booking_details"] = {
                "confirmed": True,
                "hotel_info": hotel_details.get("booking_line", "Hotel booking confirmed")
            }
        
        # Extract decision summary
        lines = reasoning.split('\n')
        for line in lines:
            if any(word in line.lower() for word in ["booked", "confirmed", "arranged", "selected"]):
                analysis["decision_summary"] = line.strip()[:100] + "..." if len(line) > 100 else line.strip()
                break
        
        if not analysis["decision_summary"]:
            analysis["decision_summary"] = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
        
        # Assess confidence based on booking success and tool usage
        if analysis["booking_details"].get("confirmed", False) and len(analysis["tools_used"]) >= 2:
            analysis["confidence_level"] = "high"
        elif len(analysis["tools_used"]) >= 1:
            analysis["confidence_level"] = "medium"
        else:
            analysis["confidence_level"] = "low"
        
        return analysis

    async def _run_crew_agent_with_streaming(self, flight_id: str, disruption: Dict[str, Any], reasoning_callback):
        """Run crew agent with reasoning streaming"""
        import io
        import sys
        import re
        import asyncio
        
        # Capture the agent's verbose output
        old_stdout = sys.stdout
        captured_output = io.StringIO()
        
        try:
            # Redirect stdout to capture LangChain's verbose output
            sys.stdout = captured_output
            
            # Parse reasoning steps in real-time using a separate task
            async def parse_and_stream():
                """Parse captured output and stream reasoning steps"""
                last_position = 0
                while True:
                    current_output = captured_output.getvalue()
                    if len(current_output) > last_position:
                        new_content = current_output[last_position:]
                        last_position = len(current_output)
                        
                        # Clean ANSI codes and parse the new content for agent steps
                        cleaned_content = self._strip_ansi_codes(new_content)
                        await self._parse_agent_output(cleaned_content, reasoning_callback)
                    
                    await asyncio.sleep(0.1)  # Check every 100ms
            
            # Start the parsing task
            parsing_task = asyncio.create_task(parse_and_stream())
            
            # Run the actual agent
            crew_response = self.crew_agent.handle_disruption(flight_id, disruption)
            
            # Cancel the parsing task
            parsing_task.cancel()
            
            # Parse any remaining output
            final_output = captured_output.getvalue()
            cleaned_final_output = self._strip_ansi_codes(final_output)
            await self._parse_agent_output(cleaned_final_output, reasoning_callback)
            
            # Send completion event
            await reasoning_callback({
                "type": "reasoning_complete",
                "content": "Crew analysis completed",
                "decision": crew_response.get("reasoning", "")[:100] + "..." if len(crew_response.get("reasoning", "")) > 100 else crew_response.get("reasoning", ""),
                "stream_id": "crew_stream"
            })
            
            return crew_response
            
        finally:
            # Restore stdout
            sys.stdout = old_stdout

    async def _run_ops_agent_with_streaming(self, crew_id: str, location: str, support_type: str, context: str, reasoning_callback):
        """Run ops agent with reasoning streaming"""
        import io
        import sys
        import asyncio
        
        # Capture the agent's verbose output
        old_stdout = sys.stdout
        captured_output = io.StringIO()
        
        try:
            # Redirect stdout to capture LangChain's verbose output
            sys.stdout = captured_output
            
            # Parse reasoning steps in real-time
            async def parse_and_stream():
                """Parse captured output and stream reasoning steps"""
                last_position = 0
                while True:
                    current_output = captured_output.getvalue()
                    if len(current_output) > last_position:
                        new_content = current_output[last_position:]
                        last_position = len(current_output)
                        
                        # Clean ANSI codes and parse the new content for agent steps
                        cleaned_content = self._strip_ansi_codes(new_content)
                        await self._parse_agent_output(cleaned_content, reasoning_callback)
                    
                    await asyncio.sleep(0.1)  # Check every 100ms
            
            # Start the parsing task
            parsing_task = asyncio.create_task(parse_and_stream())
            
            # Run the actual agent
            ops_response = self.ops_agent.handle_crew_support(crew_id, location, support_type, context)
            
            # Cancel the parsing task
            parsing_task.cancel()
            
            # Parse any remaining output
            final_output = captured_output.getvalue()
            cleaned_final_output = self._strip_ansi_codes(final_output)
            await self._parse_agent_output(cleaned_final_output, reasoning_callback)
            
            # Send completion event
            await reasoning_callback({
                "type": "reasoning_complete",
                "content": "Operations support analysis completed",
                "decision": ops_response.get("reasoning", "")[:100] + "..." if len(ops_response.get("reasoning", "")) > 100 else ops_response.get("reasoning", ""),
                "stream_id": "ops_stream"
            })
            
            return ops_response
            
        finally:
            # Restore stdout
            sys.stdout = old_stdout

    async def _parse_agent_output(self, output: str, reasoning_callback):
        """Parse LangChain agent output and create streaming events"""
        # Strip ANSI escape codes from the entire output first
        cleaned_output = self._strip_ansi_codes(output)
        lines = cleaned_output.strip().split('\n')
        last_action = None
        
        for line in lines:
            if not line.strip():
                continue
                
            # Parse different types of agent reasoning
            if "Entering new AgentExecutor chain" in line:
                await reasoning_callback({
                    "type": "reasoning_step",
                    "step": "chain_start",
                    "content": "Agent execution chain initiated",
                    "stream_id": "agent_stream"
                })
                
            elif line.startswith("Action:"):
                action = line.replace("Action:", "").strip()
                last_action = action  # Store for use with Action Input
                await reasoning_callback({
                    "type": "reasoning_step",
                    "step": "action",
                    "content": f"Using tool: {action}",
                    "stream_id": "agent_stream"
                })
                # Also send as tokens
                await reasoning_callback({
                    "type": "token",
                    "content": f"Action: {action}\n\n",
                    "stream_id": "agent_stream"
                })
                
            elif line.startswith("Action Input:"):
                input_data = line.replace("Action Input:", "").strip()
                # Convert JSON input to human-readable description
                readable_input = self._convert_json_input_to_readable(input_data, last_action)
                await reasoning_callback({
                    "type": "token", 
                    "content": f"{readable_input}\n\n",
                    "stream_id": "agent_stream"
                })
                
            elif line.startswith("Observation:"):
                observation = line.replace("Observation:", "").strip()
                await reasoning_callback({
                    "type": "token",
                    "content": f"Observation: {observation}\n\n",
                    "stream_id": "agent_stream"
                })
                
            elif line.startswith("Thought:"):
                thought = line.replace("Thought:", "").strip()
                await reasoning_callback({
                    "type": "reasoning_step",
                    "step": "thought",
                    "content": "Agent is thinking...",
                    "stream_id": "agent_stream"
                })
                await reasoning_callback({
                    "type": "token",
                    "content": f"Thought: {thought}\n\n",
                    "stream_id": "agent_stream"
                })
                
            elif line.startswith("Final Answer:"):
                answer = line.replace("Final Answer:", "").strip()
                await reasoning_callback({
                    "type": "reasoning_step",
                    "step": "final_answer",
                    "content": "Reaching final decision...",
                    "stream_id": "agent_stream"
                })
                await reasoning_callback({
                    "type": "token",
                    "content": f"Final Answer: {answer}\n\n",
                    "stream_id": "agent_stream"
                })
                
            elif "Finished chain" in line:
                await reasoning_callback({
                    "type": "reasoning_step",
                    "step": "chain_complete",
                    "content": "Agent execution completed",
                    "stream_id": "agent_stream"
                })
    
    def _convert_json_input_to_readable(self, json_input: str, action_name: str) -> str:
        """Convert JSON action input to human-readable description"""
        if not json_input or not action_name:
            return json_input
        
        try:
            import json
            data = json.loads(json_input)
            
            if action_name == "check_crew_legality":
                flight_id = data.get("flight_id", "unknown")
                return f"Checking crew duty time compliance for flight {flight_id}"
            
            elif action_name == "find_spare_crew":
                location = data.get("location", "unknown")
                return f"Searching for available spare crew at {location}"
            
            elif action_name == "find_repositioning":
                from_loc = data.get("from_location", "unknown")
                to_loc = data.get("to_location", "unknown")
                return f"Finding repositioning flights from {from_loc} to {to_loc}"
            
            elif action_name == "book_crew_hotel":
                crew_id = data.get("crew_id", "unknown")
                location = data.get("location", "unknown")
                return f"Booking hotel accommodation for crew {crew_id} at {location}"
            
            elif action_name == "check_hotel_availability":
                location = data.get("location", "unknown")
                return f"Checking hotel availability at {location}"
            
            else:
                # Fallback for unknown actions
                return f"Action parameters: {json_input}"
                
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, return original
            return json_input
    
    def _strip_ansi_codes(self, text: str) -> str:
        """Remove ANSI escape sequences from text"""
        import re
        
        # Remove ANSI escape sequences (comprehensive pattern)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Remove any remaining bracket sequences like [36;1m, [1;3m, [0m
        text = re.sub(r'\[[0-9;]*m', '', text)
        
        # Remove other common terminal codes
        text = re.sub(r'\[36;1m\[1;3m', '', text)  # Specific combo seen in output
        text = re.sub(r'\[0m', '', text)  # Reset codes
        
        return text