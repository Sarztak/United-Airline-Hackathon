def book_hotel(location, crew_id, hotel_inventory_df):
    """
    Attempt to book hotel for crew at a given location.

    Organization:
    - Filters hotels in the specified location with available rooms
    - Sorts by most availability
    - Returns success and booking confirmation if room found
    - Otherwise returns failure reason

    Args:
        location (str): Airport or city location
        crew_id (str): Crew member needing accommodation
        hotel_inventory_df (DataFrame): Inventory of hotels and room counts

    Returns:
        dict: {
            success: bool,
            hotel_id: str (if success),
            hotel_name: str (if success),
            confirmation: str (if success),
            failure_reason: str (if not success)
        }
    """
    available_hotels = hotel_inventory_df[
        (hotel_inventory_df['location'] == location) &
        (hotel_inventory_df['available_rooms'] > 0)
    ].sort_values('available_rooms', ascending=False)

    if available_hotels.empty:
        return {
            "success": False,
            "failure_reason": f"No available rooms at {location}"
        }

    hotel = available_hotels.iloc[0]
    return {
        "success": True,
        "hotel_id": hotel['hotel_id'],
        "hotel_name": hotel['name'],
        "confirmation": f"CONF-{crew_id}-{random.randint(1000, 9999)}"
    }