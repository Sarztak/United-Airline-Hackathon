import streamlit as st
from chat_renderer import render_step_with_progress

# Example flight info
flight_info = {
    "Flight ID": "UA456",
    "Status": "ontime",
    "Delay": "0",
    "Aircraft": "B737",
    "Origin": "SFO",
    "Destination": "DEN",
    "Gate": "B12",
    "Remarks": ""
}

# Example parsed steps
parsed_steps = [
    {
        "Thought": "I need to start by querying the crew roster for flight UA456 to understand who is assigned to this flight and their details.",
        "Action": "query_crew_roster",
        "Observation": '{"message": "No crew assigned to flight UA456."}'
    },
    {
        "Thought": "Since there are no crew members assigned to flight UA456, there are no duty hour legality issues to check. Therefore, I can conclude that there are no affected crew members for this flight.",
        "Action": "",
        "Observation": ""
    },
    {
        "Thought": "",
        "Action": "Final Answer: There are no affected crew members for flight UA456 as no crew is assigned to it.",
        "Observation": ""
    }
]

# Sidebar flight info
st.sidebar.header("Flight Info")
for k, v in flight_info.items():
    st.sidebar.text(f"{k}: {v}")

st.title("Crew Disruption Agent Reasoning")



for step in parsed_steps:
    render_step_with_progress(step, delay=1)  # 0.5 second delay per box (adjust as desired)
