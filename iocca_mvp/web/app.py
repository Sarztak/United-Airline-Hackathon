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
from orchestrator.orchestrator import Orchestrator
from agents.crew_assignment import handle_crew_assignment, handle_crew_assignment_stream
from agents.ops_support import handle_ops_support
from agents.policy_agent_llm import llm_policy_reason, llm_policy_reason_stream

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

# Initialize orchestrator
orchestrator = Orchestrator(
    crew_agent=handle_crew_assignment,
    ops_agent=handle_ops_support,
    policy_agent=llm_policy_reason
)

# Web logger
web_logger = get_agent_logger("web_interface")

# In-memory storage for demo (replace with database in production)
disruption_history = []
active_requests = {}
active_simulations = {}  # Track running day simulations

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "IOCCA MVP Dashboard",
        "active_requests": len(active_requests),
        "total_disruptions": len(disruption_history)
    })

@app.get("/streaming", response_class=HTMLResponse)
async def streaming_test(request: Request):
    """LLM Streaming test page"""
    return templates.TemplateResponse("streaming-test.html", {
        "request": request,
        "title": "LLM Streaming Test - IOCCA MVP"
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

def get_disruption_scenarios():
    """Get different disruption scenarios for testing"""
    scenarios = {
        "weather_delay": {
            "name": "Weather Delay - Crew Legal",
            "description": "Flight UA123 delayed 3.5 hours at ORD due to weather - crew can extend",
            "crew_roster": [
                {"crew_id": "C001", "assigned_flight_id": "UA123", "duty_end": "2024-08-10T07:30:00", "status": "active", "base": "ORD"},
                {"crew_id": "C002", "assigned_flight_id": "UA123", "duty_end": "2024-08-10T07:45:00", "status": "active", "base": "ORD"},
                {"crew_id": "C010", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "SFO"},
                {"crew_id": "C011", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "DEN"}
            ],
            "flight_schedule": [
                {"flight_id": "UA123", "origin": "ORD", "destination": "SFO", "scheduled_dep": "2024-08-10T10:30:00", "scheduled_arr": "2024-08-10T13:00:00"}
            ],
            "hotel_inventory": [
                {"hotel_id": "H001", "location": "ORD", "name": "Runway Inn", "available_rooms": 5},
                {"hotel_id": "H002", "location": "SFO", "name": "Jetlag Suites", "available_rooms": 2}
            ],
            "reposition_flights": [
                {"flight_id": "RP101", "origin": "DEN", "destination": "ORD", "sched_dep": "2024-08-10T08:30:00", "sched_arr": "2024-08-10T10:15:00", "seats_available": True}
            ],
            "duty_rules": {"max_duty_hours": 8, "min_rest_hours": 10}
        },
        
        "crew_timeout": {
            "name": "Crew Duty Time Violation",
            "description": "Flight UA456 delayed - crew times out, need spare crew with repositioning",
            "crew_roster": [
                {"crew_id": "C003", "assigned_flight_id": "UA456", "duty_end": "2024-08-10T14:00:00", "status": "active", "base": "LAX"},
                {"crew_id": "C004", "assigned_flight_id": "UA456", "duty_end": "2024-08-10T14:15:00", "status": "active", "base": "LAX"},
                {"crew_id": "C012", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "DEN"},
                {"crew_id": "C013", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "PHX"}
            ],
            "flight_schedule": [
                {"flight_id": "UA456", "origin": "LAX", "destination": "DEN", "scheduled_dep": "2024-08-10T16:00:00", "scheduled_arr": "2024-08-10T19:30:00"}
            ],
            "hotel_inventory": [
                {"hotel_id": "H003", "location": "LAX", "name": "Airport Plaza", "available_rooms": 3},
                {"hotel_id": "H004", "location": "DEN", "name": "Mountain View", "available_rooms": 1}
            ],
            "reposition_flights": [
                {"flight_id": "RP201", "origin": "DEN", "destination": "LAX", "sched_dep": "2024-08-10T14:00:00", "sched_arr": "2024-08-10T15:30:00", "seats_available": True},
                {"flight_id": "RP202", "origin": "PHX", "destination": "LAX", "sched_dep": "2024-08-10T14:30:00", "sched_arr": "2024-08-10T15:45:00", "seats_available": True}
            ],
            "duty_rules": {"max_duty_hours": 8, "min_rest_hours": 10}
        },
        
        "hotel_shortage": {
            "name": "Hotel Capacity Crisis",
            "description": "Flight UA789 cancelled - crew stranded but hotels full, need policy escalation",
            "crew_roster": [
                {"crew_id": "C005", "assigned_flight_id": "UA789", "duty_end": "2024-08-10T20:00:00", "status": "active", "base": "MIA"},
                {"crew_id": "C006", "assigned_flight_id": "UA789", "duty_end": "2024-08-10T20:15:00", "status": "active", "base": "MIA"},
                {"crew_id": "C014", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "ATL"},
                {"crew_id": "C015", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "DFW"}
            ],
            "flight_schedule": [
                {"flight_id": "UA789", "origin": "MIA", "destination": "ATL", "scheduled_dep": "2024-08-10T22:00:00", "scheduled_arr": "2024-08-11T00:30:00"}
            ],
            "hotel_inventory": [
                {"hotel_id": "H005", "location": "MIA", "name": "Beach Resort", "available_rooms": 0},
                {"hotel_id": "H006", "location": "ATL", "name": "City Center", "available_rooms": 0}
            ],
            "reposition_flights": [
                {"flight_id": "RP301", "origin": "ATL", "destination": "MIA", "sched_dep": "2024-08-10T20:00:00", "sched_arr": "2024-08-10T21:30:00", "seats_available": False},
                {"flight_id": "RP302", "origin": "DFW", "destination": "MIA", "sched_dep": "2024-08-10T19:30:00", "sched_arr": "2024-08-10T21:45:00", "seats_available": False}
            ],
            "duty_rules": {"max_duty_hours": 8, "min_rest_hours": 10}
        },
        
        "maintenance_delay": {
            "name": "Extended Maintenance Delay",
            "description": "Flight UA321 has 6-hour maintenance delay - crew reassignment needed",
            "crew_roster": [
                {"crew_id": "C007", "assigned_flight_id": "UA321", "duty_end": "2024-08-10T06:00:00", "status": "active", "base": "SEA"},
                {"crew_id": "C008", "assigned_flight_id": "UA321", "duty_end": "2024-08-10T06:30:00", "status": "active", "base": "SEA"},
                {"crew_id": "C016", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "SEA"},
                {"crew_id": "C017", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "PDX"}
            ],
            "flight_schedule": [
                {"flight_id": "UA321", "origin": "SEA", "destination": "JFK", "scheduled_dep": "2024-08-10T08:00:00", "scheduled_arr": "2024-08-10T16:30:00"}
            ],
            "hotel_inventory": [
                {"hotel_id": "H007", "location": "SEA", "name": "Emerald City Inn", "available_rooms": 4},
                {"hotel_id": "H008", "location": "JFK", "name": "Queens Hotel", "available_rooms": 2}
            ],
            "reposition_flights": [
                {"flight_id": "RP401", "origin": "PDX", "destination": "SEA", "sched_dep": "2024-08-10T07:00:00", "sched_arr": "2024-08-10T07:45:00", "seats_available": True}
            ],
            "duty_rules": {"max_duty_hours": 8, "min_rest_hours": 10}
        },
        
        "perfect_scenario": {
            "name": "Smooth Operations",
            "description": "Minor delay but crew legal, hotels available - everything works perfectly",
            "crew_roster": [
                {"crew_id": "C009", "assigned_flight_id": "UA555", "duty_end": "2024-08-10T06:00:00", "status": "active", "base": "BOS"},
                {"crew_id": "C020", "assigned_flight_id": "UA555", "duty_end": "2024-08-10T06:00:00", "status": "active", "base": "BOS"},
                {"crew_id": "C018", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "BOS"},
                {"crew_id": "C019", "assigned_flight_id": None, "duty_end": None, "status": "active", "base": "IAD"}
            ],
            "flight_schedule": [
                {"flight_id": "UA555", "origin": "BOS", "destination": "IAD", "scheduled_dep": "2024-08-10T09:00:00", "scheduled_arr": "2024-08-10T11:30:00"}
            ],
            "hotel_inventory": [
                {"hotel_id": "H009", "location": "BOS", "name": "Freedom Hotel", "available_rooms": 10},
                {"hotel_id": "H010", "location": "IAD", "name": "Capital Suites", "available_rooms": 8}
            ],
            "reposition_flights": [
                {"flight_id": "RP501", "origin": "IAD", "destination": "BOS", "sched_dep": "2024-08-10T07:30:00", "sched_arr": "2024-08-10T08:45:00", "seats_available": True}
            ],
            "duty_rules": {"max_duty_hours": 8, "min_rest_hours": 10}
        }
    }
    return scenarios

@app.get("/api/scenarios")
async def list_scenarios():
    """List available disruption scenarios"""
    scenarios = get_disruption_scenarios()
    return {
        "scenarios": [
            {
                "id": key,
                "name": scenario["name"],
                "description": scenario["description"]
            }
            for key, scenario in scenarios.items()
        ]
    }

@app.post("/api/disruption/simulate-stream")
async def simulate_disruption_stream(background_tasks: BackgroundTasks, scenario_id: str = "weather_delay"):
    """Simulate a disruption scenario with streaming LLM reasoning"""
    
    scenarios = get_disruption_scenarios()
    if scenario_id not in scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario_id}")
    
    disruption_data = scenarios[scenario_id]
    
    disruption_id = str(uuid.uuid4())
    
    # Create disruption record
    disruption = {
        "disruption_id": disruption_id,
        "flight_id": "UA123",
        "description": f"Flight disruption with streaming LLM reasoning - {disruption_data['description']}",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "processing",
        "stream_enabled": True
    }
    
    disruption_history.append(disruption)
    active_requests[disruption_id] = disruption
    
    # Process in background with streaming
    background_tasks.add_task(process_disruption_stream, disruption_id, disruption_data)
    
    web_logger.info("Disruption simulation with streaming started", disruption_id=disruption_id)
    
    return {
        "disruption_id": disruption_id,
        "status": "processing",
        "message": "Disruption simulation with streaming LLM reasoning started",
        "stream_enabled": True
    }

@app.post("/api/disruption/simulate")
async def simulate_disruption(background_tasks: BackgroundTasks, scenario_id: str = "weather_delay"):
    """Simulate a disruption scenario"""
    
    scenarios = get_disruption_scenarios()
    if scenario_id not in scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario_id}")
    
    disruption_data = scenarios[scenario_id]
    
    disruption_id = str(uuid.uuid4())
    
    # Create disruption record
    disruption = {
        "disruption_id": disruption_id,
        "flight_id": "UA123",
        "description": "Flight UA123 delayed 3.5 hours at ORD due to weather",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "processing"
    }
    
    disruption_history.append(disruption)
    active_requests[disruption_id] = disruption
    
    # Process in background
    background_tasks.add_task(process_disruption, disruption_id, disruption_data)
    
    web_logger.info("Disruption simulation started", disruption_id=disruption_id)
    
    return {
        "disruption_id": disruption_id,
        "status": "processing",
        "message": "Disruption simulation started"
    }

async def process_disruption_stream(disruption_id: str, data: Dict[str, Any]):
    """Process disruption in background with streaming LLM reasoning"""
    try:
        start_time = datetime.utcnow()
        
        # Create a streaming callback to send LLM reasoning to WebSocket clients
        async def llm_stream_callback(event):
            """Callback to handle LLM streaming events"""
            stream_message = json.dumps({
                "type": "llm_reasoning",
                "disruption_id": disruption_id,
                "event": event,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Broadcast to all connected WebSocket clients
            await manager.broadcast(stream_message)
            
            # Log detailed reasoning steps
            if event.get('type') == 'reasoning_step':
                web_logger.info(f"LLM Reasoning Step: {event.get('step')}", 
                               disruption_id=disruption_id,
                               step_content=event.get('content'))
            elif event.get('type') == 'token':
                # Only log tokens periodically to avoid spam
                if event.get('content', '').strip():  # Only log meaningful tokens
                    web_logger.debug(f"LLM Token: {event.get('content')}", 
                                   disruption_id=disruption_id,
                                   section=event.get('section'))
        
        # Convert data to pandas DataFrames
        import pandas as pd
        crew_df = pd.DataFrame(data["crew_roster"])
        flight_df = pd.DataFrame(data["flight_schedule"])
        reposition_df = pd.DataFrame(data["reposition_flights"])
        
        # Use streaming crew assignment agent
        crew_result = await handle_crew_assignment_stream(
            flight_id=flight_df.iloc[0]["flight_id"],
            crew_roster_df=crew_df,
            flight_schedule_df=flight_df,
            repositioning_flights_df=reposition_df,
            duty_rules=data["duty_rules"],
            stream_callback=llm_stream_callback
        )
        
        # Simulate additional reasoning steps if needed
        if crew_result["status"] == "escalation_required":
            # Stream policy reasoning
            policy_result = await llm_policy_reason_stream(
                query=f"Escalation required for flight {flight_df.iloc[0]['flight_id']} - no crew solutions available",
                context={"crew_result": crew_result},
                stream_callback=llm_stream_callback
            )
            crew_result["policy_reasoning"] = policy_result["llm_rationale"]
        
        # Create final results
        results = {
            "steps": [
                {"crew_assignment": crew_result}
            ],
            "final_status": crew_result["status"],
            "llm_reasoning_enabled": True
        }
        
        # Update disruption record
        if disruption_id in active_requests:
            active_requests[disruption_id].update({
                "status": "completed",
                "results": results,
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "final_status": results["final_status"]
            })
        
        # Send completion message
        completion_message = json.dumps({
            "type": "disruption_complete",
            "disruption_id": disruption_id,
            "results": results,
            "message": f"Disruption processing completed with LLM reasoning - Status: {results['final_status']}"
        })
        await manager.broadcast(completion_message)
        
        web_logger.info("Streaming disruption processing completed", 
                       disruption_id=disruption_id, 
                       final_status=results["final_status"])
        
    except Exception as e:
        web_logger.error("Streaming disruption processing failed", 
                        disruption_id=disruption_id, 
                        error=str(e))
        if disruption_id in active_requests:
            active_requests[disruption_id].update({
                "status": "failed",
                "error": str(e)
            })
        
        # Send error message
        error_message = json.dumps({
            "type": "disruption_error",
            "disruption_id": disruption_id,
            "error": str(e)
        })
        await manager.broadcast(error_message)

async def process_disruption(disruption_id: str, data: Dict[str, Any]):
    """Process disruption in background"""
    try:
        start_time = datetime.utcnow()
        
        # Run orchestrator
        results = orchestrator.handle_disruption(
            crew_roster=data["crew_roster"],
            flight_schedule=data["flight_schedule"],
            hotel_inventory=data["hotel_inventory"],
            reposition_flights=data["reposition_flights"],
            duty_rules=data["duty_rules"]
        )
        
        # Update disruption record
        if disruption_id in active_requests:
            active_requests[disruption_id].update({
                "status": "completed",
                "results": results,
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "final_status": results["final_status"]
            })
        
        web_logger.info("Disruption processing completed", 
                       disruption_id=disruption_id, 
                       final_status=results["final_status"])
        
    except Exception as e:
        web_logger.error("Disruption processing failed", 
                        disruption_id=disruption_id, 
                        error=str(e))
        if disruption_id in active_requests:
            active_requests[disruption_id].update({
                "status": "failed",
                "error": str(e)
            })

@app.get("/api/disruption/{disruption_id}")
async def get_disruption_status(disruption_id: str):
    """Get disruption processing status"""
    if disruption_id not in active_requests:
        raise HTTPException(status_code=404, detail="Disruption not found")
    
    return active_requests[disruption_id]

@app.get("/api/disruptions")
async def list_disruptions():
    """List all disruptions"""
    return {
        "disruptions": disruption_history,
        "total": len(disruption_history),
        "active": len([d for d in disruption_history if d.get("status") == "processing"])
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
        
        completion_message = json.dumps({
            "type": "simulation_complete",
            "simulation_id": simulation_id,
            "message": "Day simulation completed successfully"
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

@app.post("/api/llm/stream-test")
async def test_llm_streaming(query: str = "Analyze a flight delay scenario", background_tasks: BackgroundTasks = None):
    """Test endpoint for LLM streaming functionality"""
    
    stream_id = str(uuid.uuid4())
    
    # Store the stream in active requests for tracking
    active_requests[stream_id] = {
        "type": "llm_stream_test",
        "query": query,
        "status": "processing",
        "start_time": datetime.utcnow().isoformat()
    }
    
    async def test_stream_callback(event):
        """Test callback for LLM streaming"""
        stream_message = json.dumps({
            "type": "llm_test_stream",
            "stream_id": stream_id,
            "event": event,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Broadcast to WebSocket clients
        await manager.broadcast(stream_message)
        
        web_logger.info(f"LLM Test Stream Event: {event.get('type')}", 
                       stream_id=stream_id,
                       content_preview=event.get('content', '')[:50])
    
    # Start the LLM streaming test
    async def run_llm_test():
        try:
            result = await llm_policy_reason_stream(
                query=query,
                context={"test_mode": True, "scenario": "flight delay analysis"},
                stream_callback=test_stream_callback
            )
            
            # Update status
            if stream_id in active_requests:
                active_requests[stream_id].update({
                    "status": "completed",
                    "result": result,
                    "end_time": datetime.utcnow().isoformat()
                })
            
            # Send completion message
            completion_message = json.dumps({
                "type": "llm_test_complete",
                "stream_id": stream_id,
                "result": result
            })
            await manager.broadcast(completion_message)
            
        except Exception as e:
            if stream_id in active_requests:
                active_requests[stream_id].update({
                    "status": "failed",
                    "error": str(e),
                    "end_time": datetime.utcnow().isoformat()
                })
            
            error_message = json.dumps({
                "type": "llm_test_error",
                "stream_id": stream_id,
                "error": str(e)
            })
            await manager.broadcast(error_message)
    
    # Run in background
    if background_tasks:
        background_tasks.add_task(run_llm_test)
    else:
        # Run directly if no background tasks
        asyncio.create_task(run_llm_test())
    
    return {
        "stream_id": stream_id,
        "status": "processing",
        "message": f"LLM streaming test started for query: {query[:100]}...",
        "websocket_instructions": "Connect to /ws to receive streaming tokens"
    }

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