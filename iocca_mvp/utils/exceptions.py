"""
Custom exceptions for UCI MVP
"""

class UCIException(Exception):
    """Base exception for UCI application"""
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERIC_ERROR"
        self.context = context or {}

class AgentException(UCIException):
    """Exception raised by agents"""
    pass

class CrewAssignmentException(AgentException):
    """Exception related to crew assignment operations"""
    pass

class OpsupportException(AgentException):
    """Exception related to operational support"""
    pass

class PolicyException(UCIException):
    """Exception related to policy operations"""
    pass

class ConfigurationException(UCIException):
    """Exception related to configuration issues"""
    pass

class DataValidationException(UCIException):
    """Exception raised when data validation fails"""
    pass

class ExternalAPIException(UCIException):
    """Exception raised when external API calls fail"""
    pass

class DatabaseException(UCIException):
    """Exception related to database operations"""
    pass