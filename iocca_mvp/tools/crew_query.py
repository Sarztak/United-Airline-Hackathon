def query_crew_roster(flight_id=None, crew_id=None, crew_roster_df=None):
    """
    Fetch assigned crew for a flight or details for a specific crew member.
    
    Args:
        flight_id (str, optional): Flight identifier.
        crew_id (str, optional): Crew identifier.
        crew_roster_df (DataFrame): Crew data source.
    
    Returns:
        list of dicts or dict: Crew details.
    """
    if flight_id:
        crew = crew_roster_df[crew_roster_df['assigned_flight_id'] == flight_id]
        return crew.to_dict('records')
    
    elif crew_id:
        crew = crew_roster_df[crew_roster_df['crew_id'] == crew_id]
        if crew.empty:
            return {"error": f"Crew {crew_id} not found"}
        return crew.iloc[0].to_dict()
    
    else:
        return {"error": "Must specify either flight_id or crew_id"}
    

def find_spares(current_flight, crew_df):
    spares = crew_df[(crew_df["assigned_flight_id"].isnull()) & (crew_df["status"] == "active")]
    return spares.iloc[0].to_dict() if not spares.empty else None
