"""
LangChain-based Crew Assignment Agent
"""
from typing import Dict, Any, List
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_openai import ChatOpenAI
import pandas as pd
from datetime import datetime

from config import config
from tools.crew_query import query_crew_roster, find_spares
from tools.duty_checker import check_legality
from tools.reposition_finder import reposition_flight_finder
from utils.logger import get_agent_logger

logger = get_agent_logger("langchain_crew_assignment")

class CrewAssignmentAgent:
    """LangChain-powered Crew Assignment Agent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=config.openai.api_key,
            model=config.openai.model,
            temperature=config.openai.temperature
        )
        
        # Define tools for the agent
        self.tools = [
            Tool(
                name="check_crew_legality",
                description="Check if crew duty times are legal for a flight. Expects JSON input with flight_id.",
                func=self._check_crew_legality_tool
            ),
            Tool(
                name="find_spare_crew",
                description="Find available spare crew members. Expects JSON input with location.",
                func=self._find_spare_crew_tool
            ),
            Tool(
                name="find_repositioning",
                description="Find repositioning flights for crew. Expects JSON input with from_location and to_location.",
                func=self._find_repositioning_tool
            )
        ]
        
        # Create the agent using the simpler initialize_agent approach
        self.agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        
        # Store context data
        self.crew_roster_df = None
        self.flight_schedule_df = None
        self.repositioning_flights_df = None
        self.duty_rules = None
    
    def set_context(self, crew_roster, flight_schedule, repositioning_flights, duty_rules):
        """Set the operational context for the agent"""
        self.crew_roster_df = pd.DataFrame(crew_roster)
        self.flight_schedule_df = pd.DataFrame(flight_schedule)
        self.repositioning_flights_df = pd.DataFrame(repositioning_flights)
        self.duty_rules = duty_rules
    
    def handle_disruption(self, flight_id: str, disruption_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a flight disruption with structured reasoning"""
        logger.log_agent_start("crew_assignment_disruption", {
            "flight_id": flight_id,
            "disruption": disruption_info
        })
        
        # Get flight details for better context
        flight_details = self._get_flight_details(flight_id)
        
        input_text = f"""
        You are a Crew Assignment Agent responsible for analyzing flight disruptions and coordinating crew reassignments.
        
        FLIGHT DISRUPTION ANALYSIS:
        Flight ID: {flight_id}
        Route: {flight_details.get('origin', 'Unknown')} → {flight_details.get('destination', 'Unknown')}
        Original Departure: {flight_details.get('scheduled_dep', 'Unknown')}
        Disruption Type: {disruption_info.get('type', 'Unknown')}
        Disruption Description: {disruption_info.get('description', 'Unknown disruption')}
        Delay Duration: {disruption_info.get('delay_minutes', 0)} minutes
        
        REQUIRED ANALYSIS STEPS:
        1. Check current crew duty time legality using check_crew_legality tool
        2. If crew timeout detected, find spare crew at origin using find_spare_crew tool
        3. If no local spare crew, search for repositioning options using find_repositioning tool
        4. Assess crew accommodation needs for timeout situations
        
        HANDOFF REQUIREMENTS:
        - If crew needs accommodation, provide detailed context for Operations Support Agent
        - Include: affected crew IDs, location, reason for accommodation, timeline
        - Use format: "HANDOFF_TO_OPS: [crew_ids] at [location] need accommodation due to [reason]"
        
        RESPONSE FORMAT:
        Provide step-by-step reasoning, tool usage results, and clear handoff instructions if needed.
        """
        
        try:
            result = self.agent_executor.invoke({"input": input_text})
            
            # Extract handoff information from response
            handoff_info = self._extract_handoff_info(result["output"])
            
            # Extract structured response
            response = {
                "flight_id": flight_id,
                "agent": "crew_assignment",
                "reasoning": result["output"],
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed",
                "handoff_required": handoff_info["required"],
                "handoff_context": handoff_info["context"] if handoff_info["required"] else None
            }
            
            logger.log_agent_complete("crew_assignment_disruption", response, 0)
            return response
            
        except Exception as e:
            error_response = {
                "flight_id": flight_id,
                "agent": "crew_assignment", 
                "error": str(e),
                "status": "failed"
            }
            logger.log_agent_error("crew_assignment_disruption", e, {"flight_id": flight_id})
            return error_response
    
    def _check_crew_legality_tool(self, action_input: str) -> str:
        """Tool function to check crew legality"""
        import json
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input format"})
        
        flight_id = params.get("flight_id")
        if not flight_id:
            return json.dumps({"error": "Missing flight_id parameter"})
        
        if self.crew_roster_df is None or self.flight_schedule_df is None:
            return json.dumps({"error": "No crew or flight data available"})
        
        try:
            flight = self.flight_schedule_df[self.flight_schedule_df["flight_id"] == flight_id].iloc[0]
            assigned_crew = query_crew_roster(flight_id=flight_id, crew_roster_df=self.crew_roster_df)
            
            legal_crew = []
            illegal_crew = []
            
            for crew in assigned_crew:
                result = check_legality(
                    crew_id=crew["crew_id"],
                    planned_start=flight["scheduled_dep"],
                    planned_end=flight["scheduled_arr"],
                    duty_rules=self.duty_rules,
                    crew_roster_df=self.crew_roster_df
                )
                
                if result["legal"]:
                    legal_crew.append(crew["crew_id"])
                else:
                    illegal_crew.append(f"{crew['crew_id']}: {result['reason']}")
            
            return json.dumps({
                "legal_crew": legal_crew,
                "illegal_crew": illegal_crew,
                "message": f"Legal crew: {legal_crew}. Illegal crew: {illegal_crew}"
            })
            
        except Exception as e:
            return json.dumps({"error": f"Error checking crew legality: {str(e)}"})
    
    def _find_spare_crew_tool(self, action_input: str) -> str:
        """Tool function to find spare crew"""
        import json
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input format"})
        
        location = params.get("location")
        if not location:
            return json.dumps({"error": "Missing location parameter"})
        
        if self.crew_roster_df is None:
            return json.dumps({"error": "No crew data available"})
        
        try:
            spare = find_spares(current_flight=None, crew_df=self.crew_roster_df)
            if spare:
                return json.dumps({
                    "spare_crew": spare,
                    "message": f"Found spare crew: {spare['crew_id']} at {spare['base']}"
                })
            else:
                return json.dumps({"message": "No spare crew available"})
        except Exception as e:
            return json.dumps({"error": f"Error finding spare crew: {str(e)}"})
    
    def _find_repositioning_tool(self, action_input: str) -> str:
        """Tool function to find repositioning flights"""
        import json
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input format"})
        
        from_location = params.get("from_location")
        to_location = params.get("to_location")
        
        if not from_location or not to_location:
            return json.dumps({"error": "Missing from_location or to_location parameters"})
        
        if self.repositioning_flights_df is None:
            return json.dumps({"error": "No repositioning flight data available"})
        
        try:
            options = reposition_flight_finder(
                from_location=from_location,
                to_location=to_location,
                repositioning_flights_df=self.repositioning_flights_df
            )
            
            if options:
                flight_info = [f"{opt['flight_id']} ({opt['sched_dep']} - {opt['sched_arr']})" for opt in options]
                return json.dumps({
                    "repositioning_flights": options,
                    "message": f"Repositioning options: {', '.join(flight_info)}"
                })
            else:
                return json.dumps({
                    "message": f"No repositioning flights available from {from_location} to {to_location}"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Error finding repositioning flights: {str(e)}"})
    
    def _get_flight_details(self, flight_id: str) -> Dict[str, Any]:
        """Get flight details from schedule"""
        if self.flight_schedule_df is None:
            return {}
        
        try:
            flight_row = self.flight_schedule_df[self.flight_schedule_df["flight_id"] == flight_id]
            if not flight_row.empty:
                return flight_row.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error getting flight details: {e}")
        
        return {}
    
    def _extract_handoff_info(self, agent_output: str) -> Dict[str, Any]:
        """Extract handoff information from agent response"""
        handoff_required = "HANDOFF_TO_OPS:" in agent_output
        context = None
        
        if handoff_required:
            # Extract handoff context
            lines = agent_output.split('\n')
            for line in lines:
                if "HANDOFF_TO_OPS:" in line:
                    context = line.replace("HANDOFF_TO_OPS:", "").strip()
                    break
        
        return {
            "required": handoff_required,
            "context": context
        }