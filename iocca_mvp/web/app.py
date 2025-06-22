"""
FastAPI web interface for IOCCA MVP
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from typing import List, Dict, Any
import uuid
import json
import pandas as pd
from datetime import datetime

from config import config
from utils.logger import logger, get_agent_logger
from models.schemas import (
    CrewAssignmentRequest, OpsupportRequest, 
    CrewAssignmentResponse, OpsupportResponse,
    OrchestrationResult, Disruption
)

# Optional database integration (graceful fallback if not available)
try:
    from database.models import DisruptionRecord, db_manager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("Database modules not available - using in-memory storage")
from agents.crew_assignment import handle_crew_assignment
from agents.ops_support import handle_ops_support
from agents.policy_agent_llm import llm_policy_reason_stream

# Import new simulation system
try:
    from simulation.day_simulator import DaySimulator
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    print("Day simulation not available - install langchain dependencies")

# Initialize FastAPI app
app = FastAPI(
    title="IOCCA MVP - Airline Operations Multi-Agent System",
    description="Intelligent Operations Control Center Assistant",
    version="1.0.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="web/templates")

# Set up static files (create directory if it doesn't exist)
import os
static_dir = "web/static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Web logger
web_logger = get_agent_logger("web_interface")

# In-memory storage for simulations
active_simulations = {}  # Track running day simulations
simulator_instances = {}  # Track simulator instances for agent response access

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "IOCCA MVP - Day Simulation",
        "active_simulations": len([s for s in active_simulations.values() if s["status"] == "running"]),
        "total_simulations": len(active_simulations)
    })


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "config_valid": config.validate()
    }




@app.post("/api/crew-assignment")
async def crew_assignment_endpoint(request: CrewAssignmentRequest):
    """Crew assignment API endpoint"""
    try:
        web_logger.log_agent_start("crew_assignment_api", {
            "request_id": request.request_id,
            "flight_id": request.flight_id
        })
        
        # Convert to format expected by agent
        crew_roster_data = [crew.dict() for crew in request.crew_roster]
        flight_schedule_data = [flight.dict() for flight in request.flight_schedule]
        reposition_data = [flight.dict() for flight in request.repositioning_flights]
        
        # Call crew assignment agent
        result = handle_crew_assignment(
            flight_id=request.flight_id,
            crew_roster_df=pd.DataFrame(crew_roster_data),
            flight_schedule_df=pd.DataFrame(flight_schedule_data),
            repositioning_flights_df=pd.DataFrame(reposition_data),
            duty_rules=request.duty_rules.dict()
        )
        
        return CrewAssignmentResponse(
            request_id=request.request_id,
            agent_type="crew_assignment",
            **result
        )
        
    except Exception as e:
        web_logger.error("Crew assignment API error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ops-support")
async def ops_support_endpoint(request: OpsupportRequest):
    """Operations support API endpoint"""
    try:
        web_logger.log_agent_start("ops_support_api", {
            "request_id": request.request_id,
            "crew_id": request.crew_id,
            "location": request.location
        })
        
        # Convert to format expected by agent
        hotel_data = [hotel.dict() for hotel in request.hotel_inventory]
        
        # Call ops support agent
        result = handle_ops_support(
            crew_id=request.crew_id,
            location=request.location,
            hotel_inventory_df=pd.DataFrame(hotel_data)
        )
        
        return OpsupportResponse(
            request_id=request.request_id,
            agent_type="ops_support",
            **result
        )
        
    except Exception as e:
        web_logger.error("Ops support API error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/policies")
async def list_policies():
    """List available policies"""
    try:
        import json
        import os
        
        policy_file = os.path.join("policies", "policy_docs.json")
        with open(policy_file, "r") as f:
            policies = json.load(f)
            
        return {
            "policies": policies,
            "count": len(policies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load policies: {str(e)}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now - could handle commands later
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/simulation/start-day")
async def start_day_simulation(background_tasks: BackgroundTasks):
    """Start a full day simulation"""
    if not SIMULATION_AVAILABLE:
        # Fallback to simple simulation without LangChain
        return await start_simple_day_simulation(background_tasks)
    
    simulation_id = str(uuid.uuid4())
    
    # Create simulation record
    simulation_record = {
        "simulation_id": simulation_id,
        "type": "day_simulation",
        "status": "running",
        "start_time": datetime.utcnow().isoformat(),
        "events": []
    }
    
    active_simulations[simulation_id] = simulation_record
    
    # Start simulation in background
    background_tasks.add_task(run_day_simulation, simulation_id)
    
    web_logger.info("Day simulation started", simulation_id=simulation_id)
    
    return {
        "simulation_id": simulation_id,
        "status": "running",
        "message": "Day simulation started - events will stream via WebSocket"
    }

async def run_day_simulation(simulation_id: str):
    """Run the day simulation with real-time updates"""
    try:
        simulator = DaySimulator()
        
        async def simulation_callback(event):
            """Callback to handle simulation events"""
            # Add to simulation record
            if simulation_id in active_simulations:
                active_simulations[simulation_id]["events"].append(event)
            
            # Broadcast to WebSocket clients
            event_message = json.dumps({
                "type": "simulation_event",
                "simulation_id": simulation_id,
                "event": event
            })
            await manager.broadcast(event_message)
        
        # Run the simulation
        await simulator.simulate_day(callback=simulation_callback)
        
        # Mark simulation as complete
        if simulation_id in active_simulations:
            active_simulations[simulation_id]["status"] = "completed"
            active_simulations[simulation_id]["end_time"] = datetime.utcnow().isoformat()
            # Store final agent responses count
            active_simulations[simulation_id]["agent_responses_count"] = len(simulator.agent_responses)
        
        completion_message = json.dumps({
            "type": "simulation_complete",
            "simulation_id": simulation_id,
            "message": "Day simulation completed successfully",
            "summary": {
                "total_events": len(active_simulations[simulation_id].get("events", [])),
                "agent_responses": len(simulator.agent_responses),
                "crew_responses": len([r for r in simulator.agent_responses if r["agent_type"] == "crew_assignment"]),
                "ops_responses": len([r for r in simulator.agent_responses if r["agent_type"] == "ops_support"]),
                "simulation_duration": (datetime.utcnow() - datetime.fromisoformat(active_simulations[simulation_id]["start_time"])).total_seconds()
            }
        })
        await manager.broadcast(completion_message)
        
        web_logger.info("Day simulation completed", simulation_id=simulation_id)
        
    except Exception as e:
        # Mark simulation as failed
        if simulation_id in active_simulations:
            active_simulations[simulation_id]["status"] = "failed"
            active_simulations[simulation_id]["error"] = str(e)
        
        error_message = json.dumps({
            "type": "simulation_error", 
            "simulation_id": simulation_id,
            "error": str(e)
        })
        await manager.broadcast(error_message)
        
        web_logger.error("Day simulation failed", simulation_id=simulation_id, error=str(e))

@app.get("/api/simulation/{simulation_id}")
async def get_simulation_status(simulation_id: str):
    """Get simulation status and events"""
    if simulation_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return active_simulations[simulation_id]

@app.get("/api/simulations")
async def list_simulations():
    """List all simulations"""
    return {
        "simulations": list(active_simulations.values()),
        "total": len(active_simulations),
        "active": len([s for s in active_simulations.values() if s["status"] == "running"])
    }

@app.get("/api/simulation/{simulation_id}/agent-responses")
async def get_agent_responses(simulation_id: str, agent_type: str = None, flight_id: str = None):
    """Get detailed agent responses for a simulation"""
    if simulation_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    agent_responses = []
    
    # First try to get from simulator instance if available
    if simulation_id in simulator_instances:
        simulator = simulator_instances[simulation_id]
        agent_responses = [{
            "event_id": resp["event_id"],
            "agent_type": resp["agent_type"],
            "flight_id": resp["flight_id"],
            "crew_id": resp.get("crew_id"),
            "timestamp": resp["timestamp"],
            "reasoning": resp["full_response"].get("reasoning", ""),
            "status": resp["full_response"].get("status", "unknown"),
            "detailed_analysis": resp["analysis"],
            "response_time_ms": resp["analysis"].get("response_time_ms", 0),
            "confidence_level": resp["analysis"].get("confidence_level", "medium"),
            "handoff_required": resp["full_response"].get("handoff_required", False) if resp["agent_type"] == "crew_assignment" else None,
            "handoff_context": resp["full_response"].get("handoff_context") if resp["agent_type"] == "crew_assignment" else None,
            "booking_confirmed": resp["full_response"].get("booking_confirmed", False) if resp["agent_type"] == "ops_support" else None,
            "hotel_details": resp["full_response"].get("hotel_details") if resp["agent_type"] == "ops_support" else None
        } for resp in simulator.agent_responses]
    else:
        # Fallback to extracting from stored events
        simulation = active_simulations[simulation_id]
        for event in simulation.get("events", []):
            if event.get("type") in ["crew_analysis", "ops_support"]:
                response_data = {
                    "event_id": f"{event['type']}_{event.get('flight_id', 'unknown')}_{event.get('sim_time', '')}",
                    "agent_type": "crew_assignment" if event["type"] == "crew_analysis" else "ops_support",
                    "flight_id": event.get("flight_id"),
                    "crew_id": event.get("crew_id"),
                    "timestamp": event.get("sim_time"),
                    "reasoning": event.get("reasoning", ""),
                    "status": event.get("status", "unknown"),
                    "detailed_analysis": event.get("detailed_analysis", {}),
                    "response_time_ms": event.get("response_time_ms", 0),
                    "confidence_level": event.get("detailed_analysis", {}).get("confidence_level", "medium")
                }
                
                # Add specific fields based on agent type
                if event["type"] == "crew_analysis":
                    response_data.update({
                        "handoff_required": event.get("handoff_required", False),
                        "handoff_context": event.get("handoff_context")
                    })
                elif event["type"] == "ops_support":
                    response_data.update({
                        "booking_confirmed": event.get("booking_confirmed", False),
                        "hotel_details": event.get("hotel_details")
                    })
                
                agent_responses.append(response_data)
    
    # Apply filters
    if agent_type:
        agent_responses = [r for r in agent_responses if r["agent_type"] == agent_type]
    if flight_id:
        agent_responses = [r for r in agent_responses if r["flight_id"] == flight_id]
    
    return {
        "simulation_id": simulation_id,
        "agent_responses": agent_responses,
        "total_responses": len(agent_responses),
        "filters_applied": {"agent_type": agent_type, "flight_id": flight_id}
    }

@app.get("/api/simulation/{simulation_id}/events/{event_id}/details")
async def get_event_details(simulation_id: str, event_id: str):
    """Get detailed information for a specific event"""
    if simulation_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    simulation = active_simulations[simulation_id]
    
    # Find the specific event
    target_event = None
    for event in simulation.get("events", []):
        if f"{event['type']}_{event.get('flight_id', 'unknown')}_{event.get('sim_time', '')}" == event_id:
            target_event = event
            break
    
    if not target_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Return enhanced event details
    return {
        "event_id": event_id,
        "simulation_id": simulation_id,
        "event_data": target_event,
        "analysis": target_event.get("detailed_analysis", {}),
        "context": {
            "simulation_time": target_event.get("sim_time"),
            "flight_id": target_event.get("flight_id"),
            "agent_type": "crew_assignment" if target_event["type"] == "crew_analysis" else "ops_support"
        }
    }

@app.get("/api/simulation/{simulation_id}/agent-responses/export")
async def export_agent_responses(simulation_id: str, format: str = "json"):
    """Export agent responses in JSON or CSV format"""
    if simulation_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Get agent responses using the existing endpoint logic
    response_data = await get_agent_responses(simulation_id)
    agent_responses = response_data["agent_responses"]
    
    if format.lower() == "csv":
        import io
        import csv
        from fastapi.responses import StreamingResponse
        
        # Convert to CSV
        output = io.StringIO()
        if agent_responses:
            fieldnames = agent_responses[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for response in agent_responses:
                # Flatten nested objects for CSV
                flat_response = response.copy()
                if "detailed_analysis" in flat_response and isinstance(flat_response["detailed_analysis"], dict):
                    for key, value in flat_response["detailed_analysis"].items():
                        flat_response[f"analysis_{key}"] = str(value)
                    del flat_response["detailed_analysis"]
                writer.writerow(flat_response)
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=agent_responses_{simulation_id}.csv"}
        )
    
    else:  # JSON format
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={
                "simulation_id": simulation_id,
                "export_timestamp": datetime.utcnow().isoformat(),
                "agent_responses": agent_responses
            },
            headers={"Content-Disposition": f"attachment; filename=agent_responses_{simulation_id}.json"}
        )

async def start_simple_day_simulation(background_tasks: BackgroundTasks):
    """Fallback simple day simulation without LangChain"""
    simulation_id = str(uuid.uuid4())
    
    # Create simulation record
    simulation_record = {
        "simulation_id": simulation_id,
        "type": "simple_day_simulation", 
        "status": "running",
        "start_time": datetime.utcnow().isoformat(),
        "events": []
    }
    
    active_simulations[simulation_id] = simulation_record
    
    # Start simple simulation in background
    background_tasks.add_task(run_simple_day_simulation, simulation_id)
    
    web_logger.info("Simple day simulation started", simulation_id=simulation_id)
    
    return {
        "simulation_id": simulation_id,
        "status": "running", 
        "message": "Simple day simulation started - events will stream via WebSocket"
    }

async def run_simple_day_simulation(simulation_id: str):
    """Run a simple day simulation without LangChain dependencies"""
    try:
        import asyncio
        from datetime import datetime, timedelta
        import random
        
        # Generate some sample events
        flights = [
            {"flight_id": "UA1001", "origin": "ORD", "destination": "LAX"},
            {"flight_id": "UA1002", "origin": "SFO", "destination": "DEN"}, 
            {"flight_id": "UA1003", "origin": "MIA", "destination": "JFK"},
            {"flight_id": "UA1004", "origin": "ATL", "destination": "SEA"}
        ]
        
        start_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        for hour in range(4):  # 4 hour simulation
            current_time = start_time + timedelta(hours=hour)
            
            # Time update event
            time_event = {
                "type": "time_update",
                "sim_time": current_time.isoformat(),
                "hour": hour + 1,
                "message": f"Simulation Hour {hour + 1}: {current_time.strftime('%H:%M')}"
            }
            
            # Add to simulation record
            if simulation_id in active_simulations:
                active_simulations[simulation_id]["events"].append(time_event)
            
            # Broadcast event
            event_message = json.dumps({
                "type": "simulation_event",
                "simulation_id": simulation_id,
                "event": time_event
            })
            await manager.broadcast(event_message)
            
            # Random flight events
            for flight in flights:
                if random.random() < 0.7:  # 70% normal operations
                    event = {
                        "type": "normal_operation",
                        "flight_id": flight["flight_id"],
                        "origin": flight["origin"],
                        "destination": flight["destination"],
                        "status": "departed_on_time",
                        "sim_time": current_time.isoformat()
                    }
                else:  # 30% disruptions - Use live LLM reasoning
                    delay_minutes = random.randint(120, 360)
                    crew_ids = [f"C{random.randint(100, 999)}", f"C{random.randint(100, 999)}"]
                    
                    # Disruption detected
                    disruption_event = {
                        "type": "disruption_detected", 
                        "flight_id": flight["flight_id"],
                        "delay_minutes": delay_minutes,
                        "description": f"Flight delayed {delay_minutes} minutes - crew duty time exceeded",
                        "sim_time": current_time.isoformat()
                    }
                    
                    spare_captain = f"S{random.randint(200, 299)}"
                    spare_fo = f"S{random.randint(200, 299)}"
                    original_duty_start = (current_time - timedelta(hours=2)).strftime('%H:%M')
                    new_duty_end = (current_time + timedelta(hours=8, minutes=delay_minutes)).strftime('%H:%M')
                    
                    # Live LLM crew reasoning instead of hardcoded text
                    crew_query = f"""Crew duty time crisis for Flight {flight['flight_id']} ({flight['origin']} to {flight['destination']}):

SITUATION:
- Flight delayed {delay_minutes} minutes from {current_time.strftime('%H:%M')} to {(current_time + timedelta(minutes=delay_minutes)).strftime('%H:%M')}
- Current crew: Captain {crew_ids[0]}, First Officer {crew_ids[1]}
- Crew duty started at {original_duty_start}, would end at {new_duty_end} ({2 + (8 + delay_minutes/60):.1f} hours total)
- FAA Part 117 limit: 14 hours maximum duty time
- Available spare crew: Captain {spare_captain}, First Officer {spare_fo}

REGULATORY ANALYSIS NEEDED:
- Assess duty time violation severity
- Evaluate crew replacement options  
- Consider cost vs compliance implications
- Recommend optimal resolution"""

                    # Create LLM streaming callback for this disruption
                    async def crew_llm_callback(event):
                        """Stream LLM reasoning for crew analysis"""
                        crew_stream_event = {
                            "type": "llm_crew_reasoning",
                            "flight_id": flight["flight_id"],
                            "sim_time": current_time.isoformat(),
                            "llm_event": event
                        }
                        
                        # Add to simulation record
                        if simulation_id in active_simulations:
                            active_simulations[simulation_id]["events"].append(crew_stream_event)
                        
                        # Broadcast live reasoning
                        stream_message = json.dumps({
                            "type": "simulation_event",
                            "simulation_id": simulation_id,
                            "event": crew_stream_event
                        })
                        await manager.broadcast(stream_message)
                    
                    # Get live LLM reasoning for crew assignment
                    crew_llm_result = await llm_policy_reason_stream(
                        query=crew_query,
                        context={
                            "flight": flight,
                            "delay_minutes": delay_minutes,
                            "crew_ids": crew_ids,
                            "spare_crew": [spare_captain, spare_fo],
                            "simulation_mode": True
                        },
                        stream_callback=crew_llm_callback
                    )

                    crew_event = {
                        "type": "crew_analysis",
                        "flight_id": flight["flight_id"],
                        "agent": "crew_assignment_llm", 
                        "reasoning": crew_llm_result["llm_rationale"],
                        "decision": crew_llm_result["llm_decision"],
                        "crew_reassigned": True,
                        "original_crew": crew_ids,
                        "spare_crew": [spare_captain, spare_fo],
                        "status": "completed",
                        "sim_time": current_time.isoformat(),
                        "stream_id": crew_llm_result.get("stream_id"),
                        "llm_powered": True
                    }
                    
                    confirmation_num = f"CONF-{flight['origin']}-{random.randint(100000, 999999)}"
                    
                    # Live LLM ops support reasoning
                    ops_query = f"""Operations support required for stranded crew from Flight {flight['flight_id']}:

CREW ACCOMMODATION SITUATION:
- Crew members: Captain {crew_ids[0]}, First Officer {crew_ids[1]}
- Location: {flight['origin']} airport
- Duty timeout occurred, next assignment: {(current_time + timedelta(hours=10)).strftime('%H:%M')} tomorrow
- Need: 2 single rooms, crew-rate qualified accommodation
- Timeline: Check-in {(current_time + timedelta(hours=1)).strftime('%H:%M')} today, Check-out {(current_time + timedelta(hours=9)).strftime('%H:%M')} tomorrow

AVAILABLE OPTIONS:
- Airport hotels: Limited availability, crew rates $99-$149/night
- Downtown hotels: More availability, $179-$220/night + transportation
- Extended stay options: $79/night + transportation costs

ANALYSIS NEEDED:
- Compare cost-effectiveness of options
- Evaluate transportation logistics  
- Consider crew rest requirements
- Recommend optimal accommodation solution"""

                    # Create ops LLM streaming callback
                    async def ops_llm_callback(event):
                        """Stream LLM reasoning for ops support"""
                        ops_stream_event = {
                            "type": "llm_ops_reasoning",
                            "flight_id": flight["flight_id"],
                            "crew_ids": crew_ids,
                            "sim_time": current_time.isoformat(),
                            "llm_event": event
                        }
                        
                        # Add to simulation record
                        if simulation_id in active_simulations:
                            active_simulations[simulation_id]["events"].append(ops_stream_event)
                        
                        # Broadcast live reasoning
                        stream_message = json.dumps({
                            "type": "simulation_event",
                            "simulation_id": simulation_id,
                            "event": ops_stream_event
                        })
                        await manager.broadcast(stream_message)
                    
                    # Get live LLM reasoning for ops support
                    ops_llm_result = await llm_policy_reason_stream(
                        query=ops_query,
                        context={
                            "crew_ids": crew_ids,
                            "location": flight["origin"],
                            "confirmation_num": confirmation_num,
                            "simulation_mode": True
                        },
                        stream_callback=ops_llm_callback
                    )

                    ops_event = {
                        "type": "ops_support",
                        "flight_id": flight["flight_id"],
                        "crew_ids": crew_ids,
                        "location": flight["origin"],
                        "agent": "ops_support_llm",
                        "reasoning": ops_llm_result["llm_rationale"],
                        "decision": ops_llm_result["llm_decision"],
                        "hotel_booked": True,
                        "hotel_name": f"Crew Rest Lodge {flight['origin']}",
                        "confirmation": confirmation_num,
                        "status": "completed",
                        "sim_time": current_time.isoformat(),
                        "stream_id": ops_llm_result.get("stream_id"),
                        "llm_powered": True
                    }
                    
                    # Resolution summary with LLM insights
                    resolution_event = {
                        "type": "disruption_resolved",
                        "flight_id": flight["flight_id"],
                        "resolution": f"✅ RESOLVED with AI Analysis: Spare crew {spare_captain}/{spare_fo} assigned, original crew accommodated at {flight['origin']}",
                        "actions_taken": [
                            "AI-powered duty time violation analysis completed",
                            "LLM evaluated spare crew options and regulatory compliance",  
                            "AI-optimized hotel booking with cost analysis",
                            "Live reasoning streamed to operations center"
                        ],
                        "llm_powered": True,
                        "crew_decision_summary": crew_llm_result["llm_decision"][:100] + "...",
                        "ops_decision_summary": ops_llm_result["llm_decision"][:100] + "...",
                        "sim_time": current_time.isoformat()
                    }
                    
                    # First broadcast disruption detection
                    if simulation_id in active_simulations:
                        active_simulations[simulation_id]["events"].append(disruption_event)
                    
                    event_message = json.dumps({
                        "type": "simulation_event",
                        "simulation_id": simulation_id,
                        "event": disruption_event
                    })
                    await manager.broadcast(event_message)
                    await asyncio.sleep(2)  # Brief pause before LLM analysis starts
                    
                    # Note: crew_llm_callback and ops_llm_callback will stream tokens in real-time
                    # The LLM reasoning is already streamed above via the callbacks
                    
                    # After LLM analysis is complete, broadcast the final events
                    final_events = [crew_event, ops_event, resolution_event]
                    
                    for i, event_item in enumerate(final_events):
                        # Add event to simulation record
                        if simulation_id in active_simulations:
                            active_simulations[simulation_id]["events"].append(event_item)
                        
                        # Broadcast event
                        event_message = json.dumps({
                            "type": "simulation_event",
                            "simulation_id": simulation_id,
                            "event": event_item
                        })
                        await manager.broadcast(event_message)
                        
                        # Brief delay between final events
                        if i < len(final_events) - 1:
                            await asyncio.sleep(1)
                    
                    continue  # Skip the normal single-event processing
                
                # Normal single event processing (for on-time departures)
                if simulation_id in active_simulations:
                    active_simulations[simulation_id]["events"].append(event)
                
                event_message = json.dumps({
                    "type": "simulation_event",
                    "simulation_id": simulation_id,
                    "event": event
                })
                await manager.broadcast(event_message)
                
                await asyncio.sleep(0.5)  # Quick delay for normal events
            
            await asyncio.sleep(8)  # Wait 8 seconds per "hour"
        
        # Mark simulation as complete
        if simulation_id in active_simulations:
            active_simulations[simulation_id]["status"] = "completed"
            active_simulations[simulation_id]["end_time"] = datetime.utcnow().isoformat()
        
        completion_message = json.dumps({
            "type": "simulation_complete",
            "simulation_id": simulation_id,
            "message": "Day simulation completed successfully"
        })
        await manager.broadcast(completion_message)
        
        web_logger.info("Simple day simulation completed", simulation_id=simulation_id)
        
    except Exception as e:
        # Mark simulation as failed
        if simulation_id in active_simulations:
            active_simulations[simulation_id]["status"] = "failed"
            active_simulations[simulation_id]["error"] = str(e)
        
        error_message = json.dumps({
            "type": "simulation_error",
            "simulation_id": simulation_id, 
            "error": str(e)
        })
        await manager.broadcast(error_message)
        
        web_logger.error("Simple day simulation failed", simulation_id=simulation_id, error=str(e))


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "rag": {
            "embedding_model": config.rag.embedding_model,
            "confidence_threshold": config.rag.confidence_threshold
        },
        "app": {
            "debug": config.app.debug,
            "max_workers": config.app.max_workers,
            "timeout_seconds": config.app.timeout_seconds
        },
        "openai": {
            "model": config.openai.model,
            "max_tokens": config.openai.max_tokens,
            "temperature": config.openai.temperature,
            "api_key_configured": bool(config.openai.api_key)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.app.host, port=config.app.port)