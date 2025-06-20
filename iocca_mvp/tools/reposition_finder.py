def reposition_flight_finder(from_location, to_location, repositioning_flights_df):
    """
    Find repositioning flight options for crew.

    Organization:
    - Filters flights matching origin and destination
    - Only returns flights with available seats
    - Sorts and returns all matching options as a list of dicts

    Args:
        from_location (str): Current crew location (e.g. "DEN")
        to_location (str): Needed crew location (e.g. "SFO")
        repositioning_flights_df (DataFrame): Data containing repositioning flight options

    Returns:
        list of dicts: [
            {
                'flight_id': str,
                'origin': str,
                'destination': str,
                'sched_dep': str,
                'sched_arr': str,
                'seats_available': bool
            },
            ...
        ]
    """
    reposition_options = repositioning_flights_df[
        (repositioning_flights_df['origin'] == from_location) &
        (repositioning_flights_df['destination'] == to_location) &
        (repositioning_flights_df['seats_available'] == True)
    ]
    
    return reposition_options.to_dict('records')
