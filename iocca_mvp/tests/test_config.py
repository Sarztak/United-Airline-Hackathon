"""
Unit tests for configuration module
"""
import pytest
import os
from unittest.mock import patch
from config import Config

class TestConfig:
    
    def test_config_initialization(self):
        """Test configuration initialization"""
        config = Config()
        
        # Test default values
        assert config.rag.embedding_model == "all-MiniLM-L6-v2"
        assert config.rag.confidence_threshold == 0.55
        assert config.app.max_workers == 4
        assert config.app.timeout_seconds == 30
        
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'CONFIDENCE_THRESHOLD': '0.7',
        'MAX_WORKERS': '8'
    })
    def test_config_from_env(self):
        """Test configuration loading from environment variables"""
        config = Config()
        
        assert config.openai.api_key == 'test-key'
        assert config.rag.confidence_threshold == 0.7
        assert config.app.max_workers == 8
        
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            config = Config()
            assert config.validate() == True
            
    def test_config_validation_failure(self):
        """Test failed configuration validation"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            config = Config()
            assert config.validate() == False
            
    def test_invalid_confidence_threshold(self):
        """Test invalid confidence threshold"""
        with patch.dict(os.environ, {'CONFIDENCE_THRESHOLD': '1.5'}):
            config = Config()
            assert config.validate() == False