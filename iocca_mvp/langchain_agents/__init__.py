"""
LangChain-based multi-agent system
"""
from .crew_assignment_agent import CrewAssignmentAgent
from .ops_support_agent import OpsupportAgent

__all__ = ['CrewAssignmentAgent', 'OpsupportAgent']