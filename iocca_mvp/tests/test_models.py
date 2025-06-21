"""
Unit tests for data models and schemas
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from models.schemas import (
    CrewMember, Flight, Hotel, RepositioningFlight, DutyRules,
    CrewStatus, FlightStatus, validate_crew_roster
)

class TestCrewMember:
    
    def test_valid_crew_member(self):
        """Test valid crew member creation"""
        crew = CrewMember(
            crew_id="C001",
            assigned_flight_id="UA123",
            duty_end="2024-08-10T07:30:00",
            status=CrewStatus.ACTIVE,
            base="ORD",
            role="pilot"
        )
        
        assert crew.crew_id == "C001"
        assert crew.status == CrewStatus.ACTIVE
        assert crew.base == "ORD"
        
    def test_invalid_duty_end_format(self):
        """Test invalid duty end time format"""
        with pytest.raises(ValidationError):
            CrewMember(
                crew_id="C001",
                duty_end="invalid-date",
                status=CrewStatus.ACTIVE,
                base="ORD"
            )
            
    def test_crew_member_without_flight(self):
        """Test crew member without assigned flight"""
        crew = CrewMember(
            crew_id="C001",
            assigned_flight_id=None,
            duty_end=None,
            status=CrewStatus.ACTIVE,
            base="ORD"
        )
        
        assert crew.assigned_flight_id is None
        assert crew.duty_end is None

class TestFlight:
    
    def test_valid_flight(self):
        """Test valid flight creation"""
        flight = Flight(
            flight_id="UA123",
            origin="ORD",
            destination="SFO",
            scheduled_dep="2024-08-10T10:30:00",
            scheduled_arr="2024-08-10T13:00:00"
        )
        
        assert flight.flight_id == "UA123"
        assert flight.origin == "ORD"
        assert flight.destination == "SFO"
        assert flight.status == FlightStatus.SCHEDULED
        
    def test_invalid_time_format(self):
        """Test invalid time format"""
        with pytest.raises(ValidationError):
            Flight(
                flight_id="UA123",
                origin="ORD",
                destination="SFO",
                scheduled_dep="invalid-time",
                scheduled_arr="2024-08-10T13:00:00"
            )

class TestHotel:
    
    def test_valid_hotel(self):
        """Test valid hotel creation"""
        hotel = Hotel(
            hotel_id="H001",
            location="ORD",
            name="Airport Hotel",
            available_rooms=5
        )
        
        assert hotel.hotel_id == "H001"
        assert hotel.location == "ORD"
        assert hotel.available_rooms == 5
        
    def test_negative_rooms(self):
        """Test negative available rooms"""
        with pytest.raises(ValidationError):
            Hotel(
                hotel_id="H001",
                location="ORD",
                name="Airport Hotel",
                available_rooms=-1
            )

class TestDutyRules:
    
    def test_valid_duty_rules(self):
        """Test valid duty rules creation"""
        rules = DutyRules(
            max_duty_hours=8,
            min_rest_hours=10
        )
        
        assert rules.max_duty_hours == 8
        assert rules.min_rest_hours == 10
        
    def test_zero_duty_hours(self):
        """Test zero duty hours"""
        with pytest.raises(ValidationError):
            DutyRules(
                max_duty_hours=0,
                min_rest_hours=10
            )

class TestValidationFunctions:
    
    def test_validate_crew_roster_success(self):
        """Test successful crew roster validation"""
        crew_data = [
            {
                "crew_id": "C001",
                "assigned_flight_id": "UA123",
                "duty_end": "2024-08-10T07:30:00",
                "status": "active",
                "base": "ORD"
            },
            {
                "crew_id": "C002",
                "assigned_flight_id": None,
                "duty_end": None,
                "status": "active",
                "base": "SFO"
            }
        ]
        
        crew_roster = validate_crew_roster(crew_data)
        
        assert len(crew_roster) == 2
        assert all(isinstance(crew, CrewMember) for crew in crew_roster)
        assert crew_roster[0].crew_id == "C001"
        assert crew_roster[1].crew_id == "C002"
        
    def test_validate_crew_roster_failure(self):
        """Test failed crew roster validation"""
        crew_data = [
            {
                "crew_id": "C001",
                "duty_end": "invalid-date",
                "status": "active",
                "base": "ORD"
            }
        ]
        
        with pytest.raises(ValidationError):
            validate_crew_roster(crew_data)