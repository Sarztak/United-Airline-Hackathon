"""
Structured logging system for IOCCA MVP
"""
import logging
import sys
import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from config import config

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for log records"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logging() -> structlog.BoundLogger:
    """Setup structured logging configuration"""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        handlers=[],
        format="%(message)s"
    )
    
    # Create handler
    if config.logging.log_file:
        handler = logging.FileHandler(config.logging.log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on config
    if config.logging.format.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    # Get root logger and add handler
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if config.logging.format.lower() == "json" 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

class AgentLogger:
    """Specialized logger for agent operations"""
    
    def __init__(self, agent_name: str):
        self.logger = structlog.get_logger(agent_name)
        self.agent_name = agent_name
    
    # Standard logging methods
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def log_agent_start(self, task: str, context: Optional[Dict[str, Any]] = None):
        """Log agent task start"""
        self.logger.info(
            "Agent task started",
            agent=self.agent_name,
            task=task,
            context=context or {}
        )
    
    def log_agent_complete(self, task: str, result: Dict[str, Any], duration: float):
        """Log agent task completion"""
        self.logger.info(
            "Agent task completed",
            agent=self.agent_name,
            task=task,
            result=result,
            duration_ms=round(duration * 1000, 2)
        )
    
    def log_agent_error(self, task: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log agent error"""
        self.logger.error(
            "Agent task failed",
            agent=self.agent_name,
            task=task,
            error=str(error),
            error_type=type(error).__name__,
            context=context or {},
            exc_info=True
        )
    
    def log_policy_retrieval(self, query: str, policy_id: str, score: float):
        """Log policy retrieval"""
        self.logger.info(
            "Policy retrieved",
            agent=self.agent_name,
            query=query,
            policy_id=policy_id,
            confidence_score=score
        )
        
    def log_llm_call(self, model: str, prompt: str, response: str, tokens_used: int = 0):
        """Log LLM API call"""
        self.logger.info(
            "LLM API call",
            agent=self.agent_name,
            model=model,
            prompt_length=len(prompt),
            response_length=len(response),
            tokens_used=tokens_used
        )
    
    def log_llm_stream_start(self, model: str, prompt: str, stream_id: str):
        """Log start of LLM streaming"""
        self.logger.info(
            "LLM stream started",
            agent=self.agent_name,
            model=model,
            prompt_length=len(prompt),
            stream_id=stream_id
        )
    
    def log_llm_token(self, stream_id: str, token: str, token_index: int):
        """Log individual LLM token"""
        self.logger.debug(
            "LLM token received",
            agent=self.agent_name,
            stream_id=stream_id,
            token=token,
            token_index=token_index
        )
    
    def log_llm_stream_complete(self, stream_id: str, full_response: str, tokens_used: int, duration: float):
        """Log completion of LLM streaming"""
        self.logger.info(
            "LLM stream completed",
            agent=self.agent_name,
            stream_id=stream_id,
            response_length=len(full_response),
            tokens_used=tokens_used,
            duration_ms=round(duration * 1000, 2),
            avg_tokens_per_second=round(tokens_used / duration, 2) if duration > 0 else 0
        )
    
    def log_reasoning_step(self, step_name: str, step_content: str, stream_id: str = None):
        """Log a reasoning step during LLM processing"""
        self.logger.info(
            "Reasoning step",
            agent=self.agent_name,
            step_name=step_name,
            step_content=step_content,
            stream_id=stream_id
        )

# Global logger instance
logger = setup_logging()

def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get a specialized logger for an agent"""
    return AgentLogger(agent_name)