"""
LangChain-based Operations Support Agent
"""
from typing import Dict, Any
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage
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
                description="Book hotel accommodation for crew members",
                func=self._book_hotel_tool
            ),
            Tool(
                name="check_hotel_availability",
                description="Check hotel availability at a location",
                func=self._check_hotel_availability_tool
            )
        ]
        
        # Create the agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an Operations Support Agent for United Airlines.

Your responsibilities:
1. Book hotels for stranded or repositioned crew
2. Arrange alternative accommodations when hotels are full
3. Coordinate crew logistics during disruptions
4. Ensure crew have proper rest facilities

When crew need accommodation:
1. First try to book at preferred crew hotels
2. If unavailable, find alternative accommodations
3. Consider crew rest requirements and transportation
4. Escalate if no suitable options available

Always prioritize crew safety and rest requirements."""),
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
        self.hotel_inventory_df = None
    
    def set_context(self, hotel_inventory):
        """Set the operational context for the agent"""
        self.hotel_inventory_df = pd.DataFrame(hotel_inventory)
    
    def handle_crew_support(self, crew_id: str, location: str, support_type: str = "accommodation") -> Dict[str, Any]:
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
    
    def _book_hotel_tool(self, crew_id: str, location: str) -> str:
        """Tool function to book hotel"""
        if self.hotel_inventory_df is None:
            return "Error: No hotel inventory data available"
        
        try:
            result = book_hotel(location, crew_id, self.hotel_inventory_df)
            
            if result["success"]:
                return f"Hotel booked successfully: {result['hotel_name']} (Confirmation: {result['confirmation']})"
            else:
                return f"Hotel booking failed: {result['failure_reason']}"
                
        except Exception as e:
            return f"Error booking hotel: {str(e)}"
    
    def _check_hotel_availability_tool(self, location: str) -> str:
        """Tool function to check hotel availability"""
        if self.hotel_inventory_df is None:
            return "Error: No hotel inventory data available"
        
        try:
            available_hotels = self.hotel_inventory_df[
                (self.hotel_inventory_df['location'] == location) &
                (self.hotel_inventory_df['available_rooms'] > 0)
            ]
            
            if available_hotels.empty:
                return f"No hotels available at {location}"
            else:
                hotel_list = []
                for _, hotel in available_hotels.iterrows():
                    hotel_list.append(f"{hotel['name']} ({hotel['available_rooms']} rooms)")
                return f"Available hotels at {location}: {', '.join(hotel_list)}"
                
        except Exception as e:
            return f"Error checking hotel availability: {str(e)}"