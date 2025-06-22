"""
LangChain-based Operations Support Agent
"""
from typing import Dict, Any
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_openai import ChatOpenAI
import pandas as pd
from datetime import datetime

from config import config
from tools.hotel_booker import book_hotel
from utils.logger import get_agent_logger

logger = get_agent_logger("langchain_ops_support")

class OpsupportAgent:
    """LangChain-powered Operations Support Agent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=config.openai.api_key,
            model=config.openai.model,
            temperature=config.openai.temperature
        )
        
        # Define tools for the agent
        self.tools = [
            Tool(
                name="book_crew_hotel",
                description="Book hotel accommodation for crew members. Expects JSON input with crew_id and location.",
                func=self._book_hotel_tool
            ),
            Tool(
                name="check_hotel_availability",
                description="Check hotel availability at a location. Expects JSON input with location.",
                func=self._check_hotel_availability_tool
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
        self.hotel_inventory_df = None
    
    def set_context(self, hotel_inventory):
        """Set the operational context for the agent"""
        self.hotel_inventory_df = pd.DataFrame(hotel_inventory)
    
    def handle_crew_support(self, crew_id: str, location: str, support_type: str = "accommodation", handoff_context: str = None) -> Dict[str, Any]:
        """Handle crew support request"""
        logger.log_agent_start("ops_support_request", {
            "crew_id": crew_id,
            "location": location,
            "support_type": support_type
        })
        
        input_text = f"""
        Crew Support Request:
        
        Crew ID: {crew_id}
        Location: {location}
        Support Type: {support_type}
        
        Please arrange appropriate support for this crew member.
        """
        
        try:
            result = self.agent_executor.invoke({"input": input_text})
            
            response = {
                "crew_id": crew_id,
                "location": location,
                "agent": "ops_support",
                "reasoning": result["output"],
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            logger.log_agent_complete("ops_support_request", response, 0)
            return response
            
        except Exception as e:
            error_response = {
                "crew_id": crew_id,
                "location": location,
                "agent": "ops_support",
                "error": str(e),
                "status": "failed"
            }
            logger.log_agent_error("ops_support_request", e, {"crew_id": crew_id})
            return error_response
    
    def _book_hotel_tool(self, action_input: str) -> str:
        """Tool function to book hotel"""
        import json
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input format"})
        
        crew_id = params.get("crew_id")
        location = params.get("location")
        
        if not crew_id or not location:
            return json.dumps({"error": "Missing crew_id or location parameters"})
        
        if self.hotel_inventory_df is None:
            return json.dumps({"error": "No hotel inventory data available"})
        
        try:
            result = book_hotel(location, crew_id, self.hotel_inventory_df)
            
            if result["success"]:
                return json.dumps({
                    "success": True,
                    "hotel_name": result["hotel_name"],
                    "confirmation": result["confirmation"],
                    "message": f"Hotel booked successfully: {result['hotel_name']} (Confirmation: {result['confirmation']})"
                })
            else:
                return json.dumps({
                    "success": False,
                    "message": f"Hotel booking failed: {result['failure_reason']}"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Error booking hotel: {str(e)}"})
    
    def _check_hotel_availability_tool(self, action_input: str) -> str:
        """Tool function to check hotel availability"""
        import json
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input format"})
        
        location = params.get("location")
        if not location:
            return json.dumps({"error": "Missing location parameter"})
        
        if self.hotel_inventory_df is None:
            return json.dumps({"error": "No hotel inventory data available"})
        
        try:
            available_hotels = self.hotel_inventory_df[
                (self.hotel_inventory_df['location'] == location) &
                (self.hotel_inventory_df['available_rooms'] > 0)
            ]
            
            if available_hotels.empty:
                return json.dumps({"message": f"No hotels available at {location}"})
            else:
                hotel_list = []
                hotels_data = []
                for _, hotel in available_hotels.iterrows():
                    hotel_list.append(f"{hotel['name']} ({hotel['available_rooms']} rooms)")
                    hotels_data.append({
                        "name": hotel['name'],
                        "available_rooms": hotel['available_rooms']
                    })
                return json.dumps({
                    "available_hotels": hotels_data,
                    "message": f"Available hotels at {location}: {', '.join(hotel_list)}"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Error checking hotel availability: {str(e)}"})
    
    def _extract_booking_details(self, agent_output: str) -> Dict[str, Any]:
        """Extract booking confirmation details from agent response"""
        confirmed = "booked successfully" in agent_output.lower() or "confirmation" in agent_output.lower()
        hotel_info = {}
        
        if confirmed:
            # Try to extract hotel name and confirmation from output
            lines = agent_output.split('\n')
            for line in lines:
                if "hotel" in line.lower() and ("booked" in line.lower() or "confirmation" in line.lower()):
                    hotel_info["booking_line"] = line.strip()
                    break
        
        return {
            "confirmed": confirmed,
            "hotel_info": hotel_info if confirmed else None
        }