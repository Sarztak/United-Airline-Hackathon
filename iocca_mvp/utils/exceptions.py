"""
Custom exceptions for IOCCA MVP
"""

class IOCCAException(Exception):
    """Base exception for IOCCA application"""
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERIC_ERROR"
        self.context = context or {}

class AgentException(IOCCAException):
    """Exception raised by agents"""
    pass

class CrewAssignmentException(AgentException):
    """Exception related to crew assignment operations"""
    pass

class OpsupportException(AgentException):
    """Exception related to operational support"""
    pass

class PolicyException(IOCCAException):
    """Exception related to policy operations"""
    pass

class ConfigurationException(IOCCAException):
    """Exception related to configuration issues"""
    pass

class DataValidationException(IOCCAException):
    """Exception raised when data validation fails"""
    pass

class ExternalAPIException(IOCCAException):
    """Exception raised when external API calls fail"""
    pass

class DatabaseException(IOCCAException):
    """Exception related to database operations"""
    pass