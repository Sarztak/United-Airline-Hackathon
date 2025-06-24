"""
Database models for IOCCA MVP
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from config import config

Base = declarative_base()

class DisruptionRecord(Base):
    """Database model for disruption records"""
    __tablename__ = "disruptions"
    
    id = Column(String, primary_key=True)
    flight_id = Column(String, nullable=False)
    disruption_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Integer, default=1)
    reported_time = Column(DateTime, default=datetime.utcnow)
    resolved_time = Column(DateTime, nullable=True)
    status = Column(String, default="reported")
    final_status = Column(String, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # JSON fields for complex data
    results = Column(Text, nullable=True)  # JSON string
    context = Column(Text, nullable=True)  # JSON string
    
    def set_results(self, results_dict):
        """Set results as JSON string"""
        self.results = json.dumps(results_dict) if results_dict else None
    
    def get_results(self):
        """Get results as dictionary"""
        return json.loads(self.results) if self.results else None
    
    def set_context(self, context_dict):
        """Set context as JSON string"""
        self.context = json.dumps(context_dict) if context_dict else None
    
    def get_context(self):
        """Get context as dictionary"""
        return json.loads(self.context) if self.context else None

class AgentPerformance(Base):
    """Database model for agent performance metrics"""
    __tablename__ = "agent_performance"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # success, error, timeout
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    tokens_used = Column(Integer, nullable=True)
    api_calls = Column(Integer, default=0)
    confidence_score = Column(Float, nullable=True)
    
    # JSON fields
    input_data = Column(Text, nullable=True)  # JSON string
    output_data = Column(Text, nullable=True)  # JSON string

class PolicyUsage(Base):
    """Database model for policy usage tracking"""
    __tablename__ = "policy_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Context
    disruption_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=True)

# Database connection and session management
class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self):
        self.engine = create_engine(config.database.url, echo=config.app.debug)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'engine'):
            self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

# Initialize database on import
try:
    db_manager.create_tables()
except Exception as e:
    print(f"Warning: Database initialization failed: {e}")
    print("Database features will be disabled")