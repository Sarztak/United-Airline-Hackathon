"""
Configuration management for IOCCA MVP
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 256
    temperature: float = 0.2
    stream: bool = True
    stream_chunk_size: int = 1
    stream_delay_ms: int = 15

@dataclass
class RAGConfig:
    """RAG system configuration"""
    embedding_model: str = "all-MiniLM-L6-v2"
    confidence_threshold: float = 0.55
    policy_file: str = "policies/policy_docs.json"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = "sqlite:///./iocca_mvp.db"

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"
    log_file: Optional[str] = None

@dataclass
class AppConfig:
    """Main application configuration"""
    debug: bool = False
    max_workers: int = 4
    timeout_seconds: int = 30
    host: str = "0.0.0.0"
    port: int = 8000

class Config:
    """Central configuration manager"""
    
    def __init__(self):
        self.openai = OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '256')),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.2')),
            stream=os.getenv('OPENAI_STREAM', 'true').lower() == 'true',
            stream_chunk_size=int(os.getenv('OPENAI_STREAM_CHUNK_SIZE', '1')),
            stream_delay_ms=int(os.getenv('OPENAI_STREAM_DELAY_MS', '15'))
        )
        
        self.rag = RAGConfig(
            embedding_model=os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.55')),
            policy_file=os.getenv('POLICY_FILE', 'policies/policy_docs.json')
        )
        
        self.database = DatabaseConfig(
            url=os.getenv('DATABASE_URL', 'sqlite:///./iocca_mvp.db')
        )
        
        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', 'json'),
            log_file=os.getenv('LOG_FILE')
        )
        
        self.app = AppConfig(
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            max_workers=int(os.getenv('MAX_WORKERS', '4')),
            timeout_seconds=int(os.getenv('TIMEOUT_SECONDS', '30')),
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '8000'))
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.openai.api_key:
            return False
        if self.rag.confidence_threshold < 0 or self.rag.confidence_threshold > 1:
            return False
        return True

# Global configuration instance
config = Config()