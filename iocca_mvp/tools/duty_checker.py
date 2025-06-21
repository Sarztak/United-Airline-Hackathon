from datetime import datetime
import pandas as pd
import random

def check_legality(crew_id, planned_start, planned_end, duty_rules, crew_roster_df):
    """
    Check legality of crew duty period.

    Organization:
    - Validates that crew ID exists in the roster
    - Parses and calculates duty time based on provided planned start/end
    - Checks if the duty duration exceeds maximum allowed
    - Optionally checks rest time since last duty_end (if available)

    Args:
        crew_id (str): Crew member ID
        planned_start (str): Scheduled duty start in '%Y-%m-%d %H:%M' format
        planned_end (str): Scheduled duty end in '%Y-%m-%d %H:%M' format
        duty_rules (dict): {'max_duty_hours': int, 'min_rest_hours': int}
        crew_roster_df (DataFrame): Crew scheduling info

    Returns:
        dict: {
            legal: bool,  # Whether duty is compliant
            reason: str,  # Explanation of legality or violation
            remaining_duty_minutes: int  # Time left within duty limit, 0 if illegal
        }
    """
    crew = crew_roster_df[crew_roster_df['crew_id'] == crew_id]
    if crew.empty:
        return {"legal": False, "reason": f"Crew {crew_id} not found"}

    crew_data = crew.iloc[0]

    # Handle both ISO format and standard format
    try:
        start_time = datetime.fromisoformat(planned_start.replace('Z', '+00:00'))
    except ValueError:
        start_time = datetime.strptime(planned_start, "%Y-%m-%d %H:%M")
    
    try:
        end_time = datetime.fromisoformat(planned_end.replace('Z', '+00:00'))
    except ValueError:
        end_time = datetime.strptime(planned_end, "%Y-%m-%d %H:%M")
    duty_duration = (end_time - start_time).total_seconds() / 3600
    max_duty = duty_rules.get('max_duty_hours', 8)

    if duty_duration > max_duty:
        return {
            "legal": False,
            "reason": f"Duty period {duty_duration:.1f}h exceeds maximum {max_duty}h",
            "remaining_duty_minutes": 0
        }

    if pd.notna(crew_data['duty_end']):
        try:
            prev_duty_end = datetime.fromisoformat(crew_data['duty_end'].replace('Z', '+00:00'))
        except ValueError:
            prev_duty_end = datetime.strptime(crew_data['duty_end'], "%Y-%m-%d %H:%M")
        rest_duration = (start_time - prev_duty_end).total_seconds() / 3600
        min_rest = duty_rules.get('min_rest_hours', 10)

        if rest_duration < min_rest:
            return {
                "legal": False,
                "reason": f"Rest period {rest_duration:.1f}h below minimum {min_rest}h",
                "remaining_duty_minutes": 0
            }

    remaining_minutes = int((max_duty - duty_duration) * 60)
    return {
        "legal": True,
        "reason": "Within duty limits",
        "remaining_duty_minutes": remaining_minutes
    }
