import json
import pandas as pd
from langchain.agents import initialize_agent, Tool, AgentType

class StatusQueryAgents():
    def __init__(self, crew_roster_df):
        self.crew_roster_df = crew_roster_df
    
        self.tools = [
            Tool(
                name="query_crew_roster",
                func=self.query_crew_roster,
                description="Fetches crew assigned to a flight or crew details. Expects JSON input with flight_id or crew_id."
            )
        ]
    

    def query_crew_roster(self, action_input: str) -> str:

        try:
            params = json.loads(action_input)
        except json.JSONDecodeError :
            return "Invalid Input format. Please input JSON as string"

        flight_id = params.get("flight_id")
        crew_id = params.get("crew_id")

        if self.crew_roster_df is None:
            return {"error": "Crew roster data not provided."}

        if flight_id:
            # Get all crew assigned to the specified flight
            matched = self.crew_roster_df[self.crew_roster_df["assigned_flight_id"] == flight_id]
            if matched.empty:
                return {"message": f"No crew assigned to flight {flight_id}."}
            return matched.to_dict(orient="records")

        if crew_id:
            # Get specific crew member details
            matched = self.crew_roster_df[self.crew_roster_df["crew_id"] == crew_id]
            if matched.empty:
                return {"message": f"Crew member {crew_id} not found."}
            return matched.iloc[0].to_dict()

        return {"error": "Please provide either flight_id or crew_id for the query."}

class ActionExecutorAgents():
    def __init__(self):
        self.tools = []
    

class RuleEvaluatorAgents():
    def __init__(self):
        self.tools = []
        
        