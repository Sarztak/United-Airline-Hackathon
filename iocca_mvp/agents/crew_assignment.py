# agents/crew_assignment.py

from tools.crew_query import query_crew_roster, find_spares
from tools.duty_checker import check_legality
from tools.reposition_finder import reposition_flight_finder
from policies.rag_policy_retriever import retrieve_policy

def handle_crew_assignment(flight_id, crew_roster_df, flight_schedule_df, repositioning_flights_df, duty_rules):
    """
    Determines if assigned crew are legal. If not, attempts to find spare crew or escalate.

    Args:
        flight_id (str): Disrupted flight
        crew_roster_df (DataFrame)
        flight_schedule_df (DataFrame)
        repositioning_flights_df (DataFrame)
        duty_rules (dict)

    Returns:
        dict: {
            status: str,
            message: str,
            assigned_crew: list of crew dicts (if applicable),
            spare_used: str (crew_id, if applicable),
            policy: dict (if escalation occurs)
        }
    """
    flight = flight_schedule_df[flight_schedule_df["flight_id"] == flight_id].iloc[0]
    dep_time = flight["scheduled_dep"]
    arr_time = flight["scheduled_arr"]

    assigned_crew = query_crew_roster(flight_id=flight_id, crew_roster_df=crew_roster_df)

    legal_crew = []
    for crew in assigned_crew:
        result = check_legality(
            crew_id=crew["crew_id"],
            planned_start=dep_time,
            planned_end=arr_time,
            duty_rules=duty_rules,
            crew_roster_df=crew_roster_df
        )
        if result["legal"]:
            legal_crew.append(crew)

    if len(legal_crew) == len(assigned_crew):
        return {
            "status": "legal",
            "message": "All assigned crew are legal.",
            "assigned_crew": legal_crew
        }

    # Try to assign a spare
    spare = find_spares(current_flight=flight_id, crew_df=crew_roster_df)
    if spare:
        return {
            "status": "reassigned",
            "message": f"Assigned spare crew member {spare['crew_id']}.",
            "assigned_crew": [spare],
            "spare_used": spare["crew_id"]
        }

    # Try repositioning
    options = reposition_flight_finder(
        from_location=spare["base"],
        to_location=flight["origin"],
        repositioning_flights_df=repositioning_flights_df
    ) if spare else []

    if options:
        return {
            "status": "repositioning_initiated",
            "message": f"Repositioning spare crew from {spare['base']} via flight {options[0]['flight_id']}.",
            "assigned_crew": [spare],
            "spare_used": spare["crew_id"]
        }

    # Escalate to policy if all fallback fails
    policy = retrieve_policy("no legal crew and repositioning unavailable")

    return {
        "status": "escalation_required",
        "message": "No legal crew or repositioning available.",
        "policy": policy
    }
