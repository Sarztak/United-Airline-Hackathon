# agents/ops_support.py

from tools.hotel_booker import book_hotel
from policies.rag_policy_retriever import retrieve_policy

def handle_ops_support(crew_id, location, hotel_inventory_df):
    """
    Handles downstream support tasks such as hotel booking.
    If hotels are unavailable, escalates based on policy.

    Args:
        crew_id (str): ID of stranded or reassigned crew
        location (str): Layover or disruption airport
        hotel_inventory_df (DataFrame): Current hotel availability

    Returns:
        dict: {
            status: str,
            message: str,
            hotel_info: dict (if booked),
            policy: dict (if escalated)
        }
    """
    result = book_hotel(location, crew_id, hotel_inventory_df)

    if result["success"]:
        return {
            "status": "booked",
            "message": f"Hotel booked for crew {crew_id} at {result['hotel_name']}.",
            "hotel_info": result
        }

    # Escalate if hotel booking fails
    policy = retrieve_policy("hotel full at layover location")

    return {
        "status": "escalation_required",
        "message": f"Hotel unavailable at {location}. Policy escalation triggered.",
        "policy": policy
    }
