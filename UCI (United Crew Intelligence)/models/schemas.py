"""
Data models and validation schemas for UCI MVP
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class CrewStatus(str, Enum):
    """Crew status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    TRAINING = "training"

class FlightStatus(str, Enum):
    """Flight status enumeration"""
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    DEPARTED = "departed"
    ARRIVED = "arrived"

class DisruptionType(str, Enum):
    """Types of disruptions"""
    WEATHER = "weather"
    MAINTENANCE = "maintenance"
    CREW = "crew"
    AIRPORT = "airport"
    OTHER = "other"

class CrewMember(BaseModel):
    """Crew member data model"""
    crew_id: str = Field(..., description="Unique crew identifier")
    assigned_flight_id: Optional[str] = Field(None, description="Currently assigned flight")
    duty_end: Optional[str] = Field(None, description="Duty end time (ISO format)")
    status: CrewStatus = Field(..., description="Crew status")
    base: str = Field(..., description="Home base airport code")
    role: Optional[str] = Field(None, description="Crew role (pilot, flight_attendant, etc.)")
    
    @validator('duty_end')
    def validate_duty_end(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('duty_end must be in ISO format')
        return v

class Flight(BaseModel):
    """Flight data model"""
    flight_id: str = Field(..., description="Unique flight identifier")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    scheduled_dep: str = Field(..., description="Scheduled departure time (ISO format)")
    scheduled_arr: str = Field(..., description="Scheduled arrival time (ISO format)")
    actual_dep: Optional[str] = Field(None, description="Actual departure time")
    actual_arr: Optional[str] = Field(None, description="Actual arrival time")
    status: FlightStatus = Field(FlightStatus.SCHEDULED, description="Flight status")
    aircraft_type: Optional[str] = Field(None, description="Aircraft type")
    
    @validator('scheduled_dep', 'scheduled_arr', 'actual_dep', 'actual_arr')
    def validate_times(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Time must be in ISO format')
        return v

class Hotel(BaseModel):
    """Hotel data model"""
    hotel_id: str = Field(..., description="Unique hotel identifier")
    location: str = Field(..., description="Hotel location (airport code)")
    name: str = Field(..., description="Hotel name")
    available_rooms: int = Field(..., ge=0, description="Number of available rooms")
    rate: Optional[float] = Field(None, ge=0, description="Room rate per night")
    amenities: Optional[List[str]] = Field(None, description="Hotel amenities")

class RepositioningFlight(BaseModel):
    """Repositioning flight data model"""
    flight_id: str = Field(..., description="Repositioning flight identifier")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    sched_dep: str = Field(..., description="Scheduled departure time")
    sched_arr: str = Field(..., description="Scheduled arrival time")
    seats_available: bool = Field(..., description="Whether seats are available")
    cost: Optional[float] = Field(None, ge=0, description="Cost of repositioning")

class DutyRules(BaseModel):
    """Duty rules data model"""
    max_duty_hours: int = Field(..., gt=0, description="Maximum duty hours")
    min_rest_hours: int = Field(..., gt=0, description="Minimum rest hours")
    max_flight_time: Optional[int] = Field(None, description="Maximum flight time")
    min_turnaround_time: Optional[int] = Field(None, description="Minimum turnaround time")

class Disruption(BaseModel):
    """Disruption event data model"""
    disruption_id: str = Field(..., description="Unique disruption identifier")
    flight_id: str = Field(..., description="Affected flight identifier")
    disruption_type: DisruptionType = Field(..., description="Type of disruption")
    description: str = Field(..., description="Disruption description")
    severity: int = Field(..., ge=1, le=5, description="Severity level (1-5)")
    estimated_delay: Optional[int] = Field(None, description="Estimated delay in minutes")
    reported_time: str = Field(..., description="When disruption was reported")
    resolved_time: Optional[str] = Field(None, description="When disruption was resolved")

class AgentRequest(BaseModel):
    """Base agent request model"""
    request_id: str = Field(..., description="Unique request identifier")
    agent_type: str = Field(..., description="Type of agent")
    priority: int = Field(1, ge=1, le=5, description="Request priority (1-5)")
    context: Dict[str, Any] = Field(default_factory=dict, description="Request context")

class CrewAssignmentRequest(AgentRequest):
    """Crew assignment agent request"""
    flight_id: str = Field(..., description="Flight requiring crew assignment")
    crew_roster: List[CrewMember] = Field(..., description="Available crew roster")
    flight_schedule: List[Flight] = Field(..., description="Flight schedule")
    repositioning_flights: List[RepositioningFlight] = Field(..., description="Available repositioning flights")
    duty_rules: DutyRules = Field(..., description="Duty rules to enforce")

class OpsupportRequest(AgentRequest):
    """Operations support agent request"""
    crew_id: str = Field(..., description="Crew member needing support")
    location: str = Field(..., description="Location where support is needed")
    hotel_inventory: List[Hotel] = Field(..., description="Available hotel inventory")
    support_type: str = Field("accommodation", description="Type of support needed")

class AgentResponse(BaseModel):
    """Base agent response model"""
    request_id: str = Field(..., description="Original request identifier")
    agent_type: str = Field(..., description="Type of agent that processed request")
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")

class CrewAssignmentResponse(AgentResponse):
    """Crew assignment agent response"""
    assigned_crew: Optional[List[CrewMember]] = Field(None, description="Assigned crew members")
    spare_used: Optional[str] = Field(None, description="Spare crew member used")
    repositioning_required: bool = Field(False, description="Whether repositioning is required")
    policy_applied: Optional[Dict[str, Any]] = Field(None, description="Policy information if applicable")

class OpsupportResponse(AgentResponse):
    """Operations support agent response"""
    hotel_info: Optional[Dict[str, Any]] = Field(None, description="Hotel booking information")
    support_provided: List[str] = Field(default_factory=list, description="Types of support provided")
    cost: Optional[float] = Field(None, description="Total cost of support")
    policy_applied: Optional[Dict[str, Any]] = Field(None, description="Policy information if applicable")

class OrchestrationResult(BaseModel):
    """Orchestration result model"""
    disruption_id: str = Field(..., description="Disruption identifier")
    flight_id: str = Field(..., description="Affected flight identifier")
    final_status: str = Field(..., description="Final resolution status")
    steps: List[Dict[str, Any]] = Field(..., description="Processing steps taken")
    total_cost: Optional[float] = Field(None, description="Total cost of resolution")
    resolution_time_ms: float = Field(..., description="Total resolution time")
    agents_involved: List[str] = Field(..., description="Agents that participated")
    
def validate_crew_roster(crew_data: List[Dict[str, Any]]) -> List[CrewMember]:
    """Validate and convert crew roster data"""
    return [CrewMember(**crew) for crew in crew_data]

def validate_flight_schedule(flight_data: List[Dict[str, Any]]) -> List[Flight]:
    """Validate and convert flight schedule data"""
    return [Flight(**flight) for flight in flight_data]

def validate_hotel_inventory(hotel_data: List[Dict[str, Any]]) -> List[Hotel]:
    """Validate and convert hotel inventory data"""
    return [Hotel(**hotel) for hotel in hotel_data]

def validate_repositioning_flights(reposition_data: List[Dict[str, Any]]) -> List[RepositioningFlight]:
    """Validate and convert repositioning flight data"""
    return [RepositioningFlight(**flight) for flight in reposition_data]