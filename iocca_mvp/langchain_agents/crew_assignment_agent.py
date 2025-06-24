"""
LangChain-based Crew Assignment Agent
"""
from typing import Dict, Any, List
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage
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
                description="Check if crew duty times are legal for a flight",
                func=self._check_crew_legality_tool
            ),
            Tool(
                name="find_spare_crew",
                description="Find available spare crew members",
                func=self._find_spare_crew_tool
            ),
            Tool(
                name="find_repositioning",
                description="Find repositioning flights for crew",
                func=self._find_repositioning_tool
            )
        ]
        
        # Create the agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a Crew Assignment Agent for United Airlines.

Your responsibilities:
1. Monitor crew duty time compliance
2. Find spare crew when needed
3. Arrange crew repositioning
4. Make real-time crew assignment decisions

When given a flight disruption:
1. First check if assigned crew are still legal
2. If not legal, find spare crew
3. If spare crew need repositioning, arrange it
4. Escalate to policy if all options fail

Always explain your reasoning step by step and provide clear recommendations."""),
            HumanMessage(content="{input}")
        ])
        
        # Create the agent
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5
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
        """Handle a flight disruption"""
        logger.log_agent_start("crew_assignment_disruption", {
            "flight_id": flight_id,
            "disruption": disruption_info
        })
        
        input_text = f"""
        Flight Disruption Analysis Needed:
        
        Flight ID: {flight_id}
        Disruption: {disruption_info.get('description', 'Unknown disruption')}
        New Departure Time: {disruption_info.get('new_departure', 'TBD')}
        Delay Duration: {disruption_info.get('delay_minutes', 0)} minutes
        
        Please analyze crew assignment implications and provide recommendations.
        """
        
        try:
            result = self.agent_executor.invoke({"input": input_text})
            
            # Extract structured response
            response = {
                "flight_id": flight_id,
                "agent": "crew_assignment",
                "reasoning": result["output"],
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
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
    
    def _check_crew_legality_tool(self, flight_id: str) -> str:
        """Tool function to check crew legality"""
        if self.crew_roster_df is None or self.flight_schedule_df is None:
            return "Error: No crew or flight data available"
        
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
            
            return f"Legal crew: {legal_crew}. Illegal crew: {illegal_crew}"
            
        except Exception as e:
            return f"Error checking crew legality: {str(e)}"
    
    def _find_spare_crew_tool(self, location: str) -> str:
        """Tool function to find spare crew"""
        if self.crew_roster_df is None:
            return "Error: No crew data available"
        
        try:
            spare = find_spares(current_flight=None, crew_df=self.crew_roster_df)
            if spare:
                return f"Found spare crew: {spare['crew_id']} at {spare['base']}"
            else:
                return "No spare crew available"
        except Exception as e:
            return f"Error finding spare crew: {str(e)}"
    
    def _find_repositioning_tool(self, from_location: str, to_location: str) -> str:
        """Tool function to find repositioning flights"""
        if self.repositioning_flights_df is None:
            return "Error: No repositioning flight data available"
        
        try:
            options = reposition_flight_finder(
                from_location=from_location,
                to_location=to_location,
                repositioning_flights_df=self.repositioning_flights_df
            )
            
            if options:
                flight_info = [f"{opt['flight_id']} ({opt['sched_dep']} - {opt['sched_arr']})" for opt in options]
                return f"Repositioning options: {', '.join(flight_info)}"
            else:
                return f"No repositioning flights available from {from_location} to {to_location}"
                
        except Exception as e:
            return f"Error finding repositioning flights: {str(e)}"