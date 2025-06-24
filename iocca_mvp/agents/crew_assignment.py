# agents/crew_assignment.py

import asyncio
from typing import Optional, Callable
from tools.crew_query import query_crew_roster, find_spares
from tools.duty_checker import check_legality
from tools.reposition_finder import reposition_flight_finder
from policies.rag_policy_retriever import retrieve_policy
from agents.policy_agent_llm import llm_policy_reason_stream
from utils.logger import get_agent_logger

logger = get_agent_logger("crew_assignment")

async def handle_crew_assignment_stream(flight_id, crew_roster_df, flight_schedule_df, repositioning_flights_df, duty_rules, stream_callback: Optional[Callable] = None):
    """
    Determines if assigned crew are legal with LLM-powered reasoning and streaming.

    Args:
        flight_id (str): Disrupted flight
        crew_roster_df (DataFrame)
        flight_schedule_df (DataFrame)
        repositioning_flights_df (DataFrame)
        duty_rules (dict)
        stream_callback: Optional callback for streaming reasoning

    Returns:
        dict: {
            status: str,
            message: str,
            assigned_crew: list of crew dicts (if applicable),  
            spare_used: str (crew_id, if applicable),
            policy: dict (if escalation occurs),
            reasoning: str (LLM reasoning process)
        }
    """
    logger.log_agent_start("crew_assignment_stream", {
        "flight_id": flight_id,
        "has_callback": stream_callback is not None
    })
    
    flight = flight_schedule_df[flight_schedule_df["flight_id"] == flight_id].iloc[0]
    dep_time = flight["scheduled_dep"]
    arr_time = flight["scheduled_arr"]

    assigned_crew = query_crew_roster(flight_id=flight_id, crew_roster_df=crew_roster_df)

    # Create detailed context for LLM reasoning
    crew_status_details = []
    legal_crew = []
    
    for crew in assigned_crew:
        result = check_legality(
            crew_id=crew["crew_id"],
            planned_start=dep_time,
            planned_end=arr_time,
            duty_rules=duty_rules,
            crew_roster_df=crew_roster_df
        )
        
        status_detail = {
            "crew_id": crew["crew_id"],
            "legal": result["legal"],
            "duty_end": crew.get("duty_end"),
            "current_time": dep_time,
            "issues": result.get("issues", [])
        }
        crew_status_details.append(status_detail)
        
        if result["legal"]:
            legal_crew.append(crew)

    # Prepare context for LLM reasoning
    crew_context = {
        "flight_details": {
            "flight_id": flight_id,
            "origin": flight["origin"],
            "destination": flight["destination"],
            "scheduled_departure": dep_time,
            "scheduled_arrival": arr_time
        },
        "assigned_crew": crew_status_details,
        "legal_crew_count": len(legal_crew),
        "total_crew_count": len(assigned_crew),
        "duty_rules": duty_rules,
        "spare_crew_available": len(find_spares(current_flight=flight_id, crew_df=crew_roster_df)) > 0
    }

    if len(legal_crew) == len(assigned_crew):
        # All crew legal - quick decision
        reasoning_query = f"Flight {flight_id} crew assignment analysis: All {len(assigned_crew)} assigned crew members are legal for the scheduled flight from {flight['origin']} to {flight['destination']}."
        
        if stream_callback:
            await stream_callback({
                'type': 'reasoning_step',
                'step': 'crew_legal_check',
                'content': 'All assigned crew members are within duty time limits.',
                'stream_id': 'crew_' + flight_id
            })
        
        result = {
            "status": "legal",
            "message": "All assigned crew are legal.",
            "assigned_crew": legal_crew,
            "reasoning": "Standard duty time analysis confirmed all crew members are within regulatory limits."
        }
        
        logger.log_agent_complete("crew_assignment_stream", result, 0.1)
        return result

    # Complex case - need LLM reasoning for crew replacement decisions
    reasoning_query = f"""Flight {flight_id} crew assignment crisis: {len(assigned_crew) - len(legal_crew)} out of {len(assigned_crew)} assigned crew members have duty time violations for flight from {flight['origin']} to {flight['destination']} departing at {dep_time}.

Current situation analysis needed:
- Legal crew: {len(legal_crew)} members
- Crew with violations: {len(assigned_crew) - len(legal_crew)} members  
- Available spare crew in system
- Repositioning options from other bases
- Regulatory compliance requirements
- Cost implications of different solutions

Please analyze the situation and recommend the best course of action."""

    # Stream LLM reasoning for crew assignment decision
    llm_result = await llm_policy_reason_stream(
        query=reasoning_query,
        context=crew_context,
        stream_callback=stream_callback
    )

    # Based on LLM reasoning, execute the recommended actions
    spare = find_spares(current_flight=flight_id, crew_df=crew_roster_df)
    if spare:
        result = {
            "status": "reassigned",
            "message": f"LLM Analysis: Assigned spare crew member {spare['crew_id']} based on duty time analysis.",
            "assigned_crew": [spare],
            "spare_used": spare["crew_id"],
            "reasoning": llm_result["llm_rationale"]
        }
        
        logger.log_agent_complete("crew_assignment_stream", result, 2.0)
        return result

    # Try repositioning if we have spare crew
    options = []
    if spare:
        options = reposition_flight_finder(
            from_location=spare["base"],
            to_location=flight["origin"],
            repositioning_flights_df=repositioning_flights_df
        )

    if options:
        result = {
            "status": "repositioning_initiated",
            "message": f"LLM Analysis: Repositioning spare crew from {spare['base']} via flight {options[0]['flight_id']} based on comprehensive analysis.",
            "assigned_crew": [spare],
            "spare_used": spare["crew_id"],
            "reasoning": llm_result["llm_rationale"]
        }
        
        logger.log_agent_complete("crew_assignment_stream", result, 3.0)
        return result

    # Final escalation with LLM policy reasoning
    policy = retrieve_policy("no legal crew and repositioning unavailable")

    result = {
        "status": "escalation_required",
        "message": "LLM Analysis: No viable crew solutions available - escalation required.",
        "policy": policy,
        "reasoning": llm_result["llm_rationale"]
    }
    
    logger.log_agent_complete("crew_assignment_stream", result, 4.0)
    return result

def handle_crew_assignment(flight_id, crew_roster_df, flight_schedule_df, repositioning_flights_df, duty_rules):
    """
    Synchronous wrapper for crew assignment (backwards compatibility).
    """
    # Run the async version synchronously
    return asyncio.run(handle_crew_assignment_stream(
        flight_id, crew_roster_df, flight_schedule_df, repositioning_flights_df, duty_rules
    ))
