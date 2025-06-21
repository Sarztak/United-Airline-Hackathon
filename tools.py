import json
from datetime import datetime, timedelta
import pandas as pd
from langchain.agents import initialize_agent, Tool, AgentType

class StatusQueryTools():
    def __init__(
            self, 
            crew_roster_df, 
            repositioning_flights_df, 
            flight_schedule_df,
            hotels_df,
            transport_df,
            policies_df,
        ):

        self.crew_roster_df = crew_roster_df
        self.reposition_flight_df = repositioning_flights_df
        self.flight_schedule_df = flight_schedule_df
        self.hotels_df = hotels_df
        self.transport_df = transport_df
        self.policies_df = policies_df
        self.affected_crew_list = list()

        self.tools = [
            Tool(
                name="query_crew_roster",
                func=self.query_crew_roster,
                description="Fetches crew assigned to a flight or crew details. Expects JSON input with flight_id or crew_id."
            ),
            Tool(
                name="duty_hour_checker",
                func=self.duty_hour_checker,
                description="Checks duty legality for provided crew. Expects JSON input with crew_ids, sched_arr, delay_minutes."
            ),
            Tool(
                name="query_spare_pool",
                func=self.query_spare_pool,
                description="Finds spare crew for a required role and aircraft type. Expects JSON input with required_role, qualified_aircraft, exclude_crew_ids."
            ),
            Tool(
                name="reposition_flight_finder",
                func=self.reposition_flight_finder,
                description="Finds repositioning flights for spare crew. Expects JSON input with from_base, to_airport, sched_dep, delay_minutes, report_buffer."
            ),
            Tool(
                name="book_hotel",
                func=self.book_hotel,
                description="Books hotel accommodation for affected crew. Expects JSON input with airport and crew_ids."
            ),
            Tool(
                name="arrange_transport",
                func=self.arrange_transport,
                description="Arranges ground transport to hotel for affected crew. Expects JSON input with airport, crew_ids, hotel."
            ),
            Tool(
                name="policy_retriever",
                func=self.policy_retriever,
                description="Retrieves relevant operational policy. Expects JSON input with a policy_query string."
            ),
            Tool(
                name="send_notification",
                func=self.send_notification,
                description="Sends a notification message. Expects JSON input with recipients and message."
            ),
            Tool(
                name="add_affected_crew",
                func=self.add_affected_crew,
                description="Adds a crew member to the affected list. Expects JSON input with crew_id, role, base."
            ),
            Tool(
                name="get_affected_crew",
                func=self.get_affected_crew,
                description="Retrieves the list of affected crew. Expects empty JSON input"
            )
        ]

    

    def add_affected_crew(self, action_input: str) -> str:
        """
        action_input = {
            "crew_id": "C001",
            "role": "captain",
            "base": "ORD"
        }
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})

        crew_id = params.get("crew_id")
        role = params.get("role")
        base = params.get("base")

        if not crew_id or not role or not base:
            return json.dumps({"error": "Missing required fields"})

        self.affected_crew_list.append({
            "crew_id": crew_id,
            "role": role,
            "base": base
        })

        return json.dumps({
            "message": f"Crew member {crew_id} added to affected list"
        })

    def get_affected_crew(self, action_input: str) -> str:
        """
        action_input = {}
        """
        return json.dumps({
            "affected_crew": self.affected_crew_list
        })

    def query_crew_roster(self, action_input: str) -> str:
        """
        LangChain-compatible tool that fetches crew assigned to a flight or crew member details.
        Expects Action Input as JSON: { "flight_id": "...", "crew_id": "..." }
        Outputs a stringified version of a list of crew member on flight with flight_id or with crew_id as id : 
        [{"crew_id": "C001", "duty_end": "2024-08-10 15:00"}, {"crew_id": "C002", "duty_end": "2024-08-10 15:00"}]
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError :
            return json.dumps({"error": "Invalid input format"})

        flight_id = params.get("flight_id")
        crew_id = params.get("crew_id")

        if self.crew_roster_df is None:
            return json.dumps({"error": "Crew roster data not provided."})

        if flight_id:
            # Get all crew assigned to the specified flight
            matched = self.crew_roster_df[self.crew_roster_df["assigned_flight_id"] == flight_id]
            if matched.empty:
                return json.dumps({"message": f"No crew assigned to flight {flight_id}."})
            return json.dumps(matched.to_dict(orient="records"))

        if crew_id:
            # Get specific crew member details
            matched = self.crew_roster_df[self.crew_roster_df["crew_id"] == crew_id]
            if matched.empty:
                return {"message": f"Crew member {crew_id} not found."}
            return json.dumps(matched.iloc[0].to_dict())

        return json.dumps({"error": "Please provide either flight_id or crew_id for the query."})
    
    def duty_hour_checker(self, action_input:str) -> str:
        """ 
        action_input : {
                        "crew_ids": ["C001", "C002"],
                        "sched_arr": "2024-08-10 14:00",
                        "delay_minutes": 210
                        }
        duty_end should be computed by checking from the crew_roaster_df
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError :
            return json.dumps({"error": "Invalid input format"})

        crew_ids = params.get("crew_ids")
        sched_arr = params.get("sched_arr")
        delay_minutes = int(params.get("delay_minutes"))

        sched_arr = datetime.strptime(sched_arr, "%Y-%m-%d %H:%M")
        delay = timedelta(minutes=delay_minutes)
        projected_arrival = sched_arr + delay

        result = {}
        for crew_id in crew_ids:
            if crew_id:
                
                try:
                    duty_end_series = self.crew_roster_df.loc[
                        self.crew_roster_df["crew_id"] == crew_id, "duty_end"
                    ]
                    
                    if duty_end_series.empty:
                        return json.dumps({"error": f"crew id {crew_id} not found"})
                    
                    duty_end = duty_end_series.iloc[0]
                    duty_end = datetime.strptime(duty_end, "%Y-%m-%d %H:%M")
                except Exception as e:
                    return json.dumps(
                        {"error": f"Error processing crew id{crew_id}; {e}"}
                    )
                
                status = "not legal" if duty_end < projected_arrival else "legal"
                
                result[crew_id] = {
                    "duty_end": duty_end.strftime("%Y-%m-%d %H:%M"),
                    "projected_arrival" : projected_arrival.strftime("%Y-%m-%d %H:%M"),
                    "status": status
                    }
        
        return json.dumps(result)

    def query_spare_pool(self, action_input: str) -> str:
        """
        action_input =     {
                "required_role": "<role>",   // e.g. "captain" or "FO"
                "qualified_aircraft": "<aircraft type>",
                "exclude_crew_ids": [ ... ]  // to avoid picking current assigned crew
            }

        """

        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})
        
        required_role = params.get("required_role")
        qualified_aircraft = params.get("qualified_aircraft")
        exclude_crew_ids = params.get("exclude_crew_ids", [])

        if not required_role or not qualified_aircraft:
            return json.dumps({"error": "Missing required_role or qualified_aircraft"})
        
        spare_crew = self.crew_roster_df[
            (self.crew_roster_df["role"] == required_role) &
            (self.crew_roster_df["qualified_aircraft"] == qualified_aircraft) &
            (~ self.crew_roster_df["crew_id"].isin(exclude_crew_ids)) &
            (self.crew_roster_df["status"] == "active") &
            (self.crew_roster_df["assigned_flight_id"].isnull())
        ]

        if spare_crew.empty:
            return json.dumps({"message": "No matching spare crew"})

        result = spare_crew[["crew_id", "name", "base", "rest_until"]].to_dict(orient="records")

        return json.dumps(result)

    def reposition_flight_finder(self, action_input: str) -> str:
        """
        action_input =  
                    {
                        "from_base": "SFO",
                        "to_airport": "ORD",
                        "sched_dep": "2024-08-10 08:00",
                        "delay_minutes": 210,
                        "report_buffer": 60
                    }
        """
        
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})
        
        from_base = params.get("from_base")
        to_airport = params.get("to_airport")
        sched_dep = params.get("sched_dep")
        delay_minutes = params.get("delay_minutes")
        report_buffer = int(params.get("report_buffer"))
        delay_minutes = int(params.get("delay_minutes"))

        sched_dep = datetime.strptime(sched_dep, "%Y-%m-%d %H:%M")
        delay = timedelta(minutes=delay_minutes)
        projected_dep = sched_dep + delay
        required_time = projected_dep - timedelta(minutes=report_buffer)

        df_copy = self.reposition_flight_df
        df_copy['sched_arr_dt'] = pd.to_datetime(df_copy['sched_arr'], format="%Y-%m-%d %H:%M")

        available_flights = df_copy[
            (df_copy['origin'] == from_base) &
            (df_copy['destination'] == to_airport) &
            (df_copy['seats_available']) &
            (df_copy['sched_arr_dt'] <= required_time)
        ].drop(columns='sched_arr_dt')

        if available_flights.empty:
            return json.dumps(
                {
                    "required_time": required_time.strftime("%Y-%m-%d %H:%M"),
                    "message": "No reposition flight found meeting required time"
                }
            )
        
        

        earliest_available_flight = (
            available_flights
            .sort_values(by='sched_arr')
            .iloc[0]
        )

        result = {
            "required_time": required_time.strftime("%Y-%m-%d %H:%M"),
            "earliest_available_flight": earliest_available_flight.to_dict()
        }


        return json.dumps(result)

    def book_hotel(self, action_input: str) -> str:
        """
        action_input = {
            "airport": "ORD",
            "crew_ids": ["C001", "C002"]
        }
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})

        airport = params.get("airport")
        crew_ids = params.get("crew_ids", [])

        if not airport or not crew_ids:
            return json.dumps({"error": "Missing airport or crew_ids"})

        rooms_needed = len(crew_ids)

        available_hotels = self.hotels_df[
            (self.hotels_df["airport"] == airport) &
            (self.hotels_df["rooms_available"] >= rooms_needed)
        ]

        if available_hotels.empty:
            return json.dumps({"message": "No rooms available at airport hotels"})
        
        selected_hotel = available_hotels["hotel_name"].iloc[0]
        result = {
            "hotel": selected_hotel,
            "rooms_booked": rooms_needed,
            "crew_ids": crew_ids,
            "message": "Hotel booked successfully"
        }

        return json.dumps(result)
    
    def arrange_transport(self, action_input: str) -> str:
        """
        action_input = {
            "airport": "ORD",
            "crew_ids": ["C001", "C002"],
            "hotel": "Airport Inn"
        }
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})

        airport = params.get("airport")
        crew_ids = params.get("crew_ids", [])
        hotel = params.get("hotel")

        if not airport or not crew_ids or not hotel:
            return json.dumps({"error": "Missing airport, crew_ids, or hotel"})

        seats_needed = len(crew_ids)

        available_pickup = self.transport_df[
            (self.transport_df['airport'] == airport) &
            (self.transport_df['seats_available'] >= seats_needed)
        ]

        if available_pickup.empty:
            return json.dumsp({"message": "No suitable transport available"})
        
        selected_pickup = available_pickup["service_name"].iloc[0]
        result = {
                    "service": selected_pickup,
                    "seats_booked": seats_needed,
                    "hotel": hotel,
                    "crew_ids": crew_ids,
                    "message": "Transport arranged successfully"
                }

        return json.dumps(result)
    
    def policy_retriever(self, action_input: str) -> str:
        """
        action_input = {
            "topic": "crew disruption at ORD"
        }
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})

        topic = params.get("topic")
        if not topic:
            return json.dumps({"error": "Missing topic"})

        matched = self.policies_df[self.policies_df["topic"] == topic]

        if matched.empty:
            return json.dumps({"message": "No policy found for requested topic"})

        policy_text = matched["policy"].iloc[0]

        result = {
            "policy": policy_text,
            "message": "Policy retrieved successfully"
        }

        return json.dumps(result)
    
    def send_notification(self, action_input: str) -> str:
        """
        action_input = {
            "recipients": ["Crew Ops", "Duty Manager"],
            "message": "..."
        }
        """
        try:
            params = json.loads(action_input)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid input format"})

        recipients = params.get("recipients")
        message = params.get("message")

        if not recipients or not message:
            return json.dumps({"error": "Missing recipients or message"})

        return json.dumps({
            "recipients": recipients,
            "message_sent": message,
            "status": "Notification sent successfully"
        })



    

class ActionExecutorAgents():
    def __init__(self):
        self.tools = []
    

class RuleEvaluatorAgents():
    def __init__(self):
        self.tools = []


if __name__ == "__main__":
    from mock_data import crew_roster_df, repositioning_flights_df, flight_schedule_df, hotels_df, transport_df, policies_df

    test_status_query_agent = StatusQueryTools(
        crew_roster_df=crew_roster_df,
        flight_schedule_df=flight_schedule_df,
        repositioning_flights_df=repositioning_flights_df,
        hotels_df = hotels_df,
        transport_df=transport_df,
        policies_df=policies_df
    )

    duty_hour_checker_result = test_status_query_agent.duty_hour_checker("""{"crew_ids": ["C001", "C002"],
                        "sched_arr": "2024-08-10 14:00",
                        "delay_minutes": 210
                        }""")
    
    query_spare_pool_result = test_status_query_agent.query_spare_pool(
        """{"required_role": "FO", "qualified_aircraft": "B737","exclude_crew_ids": ["C001", "C002"]}"""
    )
    
    repositioning_flight_result = test_status_query_agent.reposition_flight_finder("""{"from_base": "SFO", "to_airport": "ORD", "sched_dep": "2024-08-10 15:00", "delay_minutes": 210, "report_buffer": 60}""")

    hotel_booking_result = test_status_query_agent.book_hotel(
        """{
            "airport": "ORD",
            "crew_ids": ["C001", "C002"]
        }
        """
    )

    transport_booking_result = test_status_query_agent.arrange_transport(
        """{
            "airport": "ORD",
            "crew_ids": ["C001", "C002"],
            "hotel": "Airport Inn"
        }
        """
    )

    policy_result = test_status_query_agent.policy_retriever(
        """ {"topic": "crew disruption at ORD"}"""
    )

    notification_result = test_status_query_agent.send_notification(
        """{"recipients": ["Crew Ops", "Duty Manager"],
            "message": "Spare crew assigned from DEN, reposition failed, hotel booked at Airport Inn."
            }
        """
    )

    affected_crew_add = test_status_query_agent.add_affected_crew(
        """{
            "crew_id": "C001",
            "role": "captain",
            "base": "ORD"
        }"""
    )


    result = test_status_query_agent.get_affected_crew("""{}""")
    print(repositioning_flight_result)
