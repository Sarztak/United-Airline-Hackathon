from dataclasses import field, dataclass
from typing import Dict, List, Any
from langgraph.graph import END, StateGraph
from tools import StatusQueryTools
from mock_data import crew_roster_df, repositioning_flights_df, flight_schedule_df, hotels_df, transport_df, policies_df
import json

@dataclass
class CrewDisruptionState:
    flight_data: Dict[str, Any]
    crew_roster: List[Dict[str, Any]] = field(default_factory=list)
    legality_results: Dict[str, Any] = field(default_factory=dict)
    affected_crew: List[Dict[str, Any]] = field(default_factory=list)
    spare_attempts: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)

def all_legal(state: CrewDisruptionState):
    return all(r["status"] == "legal" for r in state.legality_results.values())

def any_not_legal(state: CrewDisruptionState):
    return not all_legal(state)



graph = StateGraph(CrewDisruptionState)

graph.add_node("query_crew_roster_node", query_crew_roster_node)
graph.add_node("duty_hour_checker_node", duty_hour_checker_node)
graph.add_node("spare_search_node", spare_search_node)
graph.add_node("reposition_node", reposition_node)
graph.add_node("fallback_node", fallback_node)
graph.add_node("arrange_transport_node", arrange_transport_node)
graph.add_node("policy_retriever_node", policy_retriever_node)
graph.add_node("send_notification_node", send_notification_node)
graph.add_node("final_success_node", final_success_node)

graph.set_entry_point("query_crew_roster_node")

# Example edge setup
graph.add_edge("query_crew_roster_node", "duty_hour_checker_node")
graph.add_edge("duty_hour_checker_node", "final_success_node", condition=all_legal)
graph.add_edge("duty_hour_checker_node", "spare_search_node", condition=any_not_legal)
# Add remaining edges...

executable = graph.compile()


status_tools = StatusQueryTools(
    crew_roster_df=crew_roster_df,
    flight_schedule_df=flight_schedule_df,
    repositioning_flights_df=repositioning_flights_df,
    hotels_df = hotels_df,
    transport_df=transport_df,
    policies_df=policies_df
)

def query_crew_roster_node(state: CrewDisruptionState):
    flight_id = state.flight_data.get("flight_id")
    if not flight_id:
        raise ValueError("Flight ID missing in state.flight_data")

    action_input = json.dumps({"flight_id": flight_id})
    result_str = status_tools.query_crew_roster(action_input)

    try:
        crew_roster = json.loads(result_str)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON returned from query_crew_roster: {result_str}")

    if isinstance(crew_roster, dict) and "message" in crew_roster:
        state.crew_roster = []
        state.actions_taken.append(f"query_crew_roster: {crew_roster['message']}")
    elif isinstance(crew_roster, list):
        state.crew_roster = crew_roster
        state.actions_taken.append("query_crew_roster: crew data retrieved")
    else:
        raise ValueError(f"Unexpected output from query_crew_roster: {result_str}")

    return "duty_hour_checker_node", state




for _, row in flight_schedule_df.iterrows():
    flight_data = row.to_dict()
    initial_state = CrewDisruptionState(flight_data=flight_data)
    result = executable.invoke(initial_state)

