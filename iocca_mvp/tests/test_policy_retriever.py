"""
Unit tests for RAG policy retriever
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from policies.rag_policy_retriever import retrieve_policy, FALLBACK_POLICY

class TestPolicyRetriever:
    
    @patch('policies.rag_policy_retriever.model')
    @patch('policies.rag_policy_retriever.policy_embeddings')
    @patch('policies.rag_policy_retriever.policy_docs')
    def test_retrieve_policy_high_confidence(self, mock_docs, mock_embeddings, mock_model):
        """Test policy retrieval with high confidence score"""
        # Mock data
        mock_docs.return_value = [
            {
                "id": "test_policy",
                "title": "Test Policy",
                "text": "This is a test policy"
            }
        ]
        
        mock_embeddings.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        # Mock cosine similarity to return high score
        with patch('policies.rag_policy_retriever.cosine_similarity') as mock_similarity:
            mock_similarity.return_value = np.array([[0.9]])  # High confidence
            
            result = retrieve_policy("test query")
            
            assert result["policy_id"] == "test_policy"
            assert result["title"] == "Test Policy"
            assert result["policy_text"] == "This is a test policy"
            assert result["score"] == 0.9
    
    @patch('policies.rag_policy_retriever.model')
    @patch('policies.rag_policy_retriever.policy_embeddings')
    @patch('policies.rag_policy_retriever.policy_docs')
    def test_retrieve_policy_low_confidence(self, mock_docs, mock_embeddings, mock_model):
        """Test policy retrieval with low confidence score"""
        mock_embeddings.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        # Mock cosine similarity to return low score
        with patch('policies.rag_policy_retriever.cosine_similarity') as mock_similarity:
            mock_similarity.return_value = np.array([[0.3]])  # Low confidence
            
            result = retrieve_policy("test query")
            
            # Should return fallback policy
            assert result == FALLBACK_POLICY
    
    @patch('policies.rag_policy_retriever.model')
    def test_retrieve_policy_error_handling(self, mock_model):
        """Test error handling in policy retrieval"""
        # Mock model to raise exception
        mock_model.encode.side_effect = Exception("Model error")
        
        result = retrieve_policy("test query")
        
        # Should return fallback policy on error
        assert result == FALLBACK_POLICY
    
    def test_fallback_policy_structure(self):
        """Test fallback policy structure"""
        assert "policy_id" in FALLBACK_POLICY
        assert "title" in FALLBACK_POLICY
        assert "policy_text" in FALLBACK_POLICY
        assert "score" in FALLBACK_POLICY
        assert FALLBACK_POLICY["policy_id"] == "fallback"
        assert FALLBACK_POLICY["score"] == 0.0