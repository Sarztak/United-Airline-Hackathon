# policies/rag_policy_retriever.py

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
import os
import time
from typing import Dict, Any

from config import config
from utils.logger import get_agent_logger
from utils.exceptions import PolicyException, ConfigurationException

# Set up logging
logger = get_agent_logger("rag_policy_retriever")

# Load policy documents from file
try:
    POLICY_FILE = os.path.join(os.path.dirname(__file__), config.rag.policy_file.split('/')[-1])
    with open(POLICY_FILE, "r") as f:
        policy_docs = json.load(f)
    logger.info("Policy documents loaded successfully", count=len(policy_docs))
except Exception as e:
    logger.error("Failed to load policy documents", error=str(e))
    raise ConfigurationException(f"Failed to load policy documents: {str(e)}")

# Load embedding model
try:
    model = SentenceTransformer(config.rag.embedding_model)
    logger.info("Embedding model loaded successfully", model=config.rag.embedding_model)
except Exception as e:
    logger.error("Failed to load embedding model", error=str(e))
    raise ConfigurationException(f"Failed to load embedding model: {str(e)}")

# Encode policy texts
try:
    policy_texts = [doc["text"] for doc in policy_docs]
    policy_embeddings = model.encode(policy_texts, convert_to_numpy=True)
    logger.info("Policy embeddings created successfully", count=len(policy_embeddings))
except Exception as e:
    logger.error("Failed to create policy embeddings", error=str(e))
    raise PolicyException(f"Failed to create policy embeddings: {str(e)}")

# RAG-style policy retriever with optional fallback
FALLBACK_POLICY = {
    "policy_id": "fallback",
    "title": "General Escalation",
    "policy_text": "Situation requires manual review. Escalate to duty manager for case-by-case guidance.",
    "score": 0.0
}

def retrieve_policy(query: str) -> Dict[str, Any]:
    """
    Retrieve the most relevant policy for a given query using RAG
    
    Args:
        query (str): The query string to search for
        
    Returns:
        dict: Policy information with score
    """
    start_time = time.time()
    
    logger.log_agent_start("policy_retrieval", {"query": query})
    
    try:
        # Create query embedding
        query_embedding = model.encode([query], convert_to_numpy=True)
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, policy_embeddings)[0]
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_policy = policy_docs[best_idx]
        
        # Check confidence threshold
        if best_score < config.rag.confidence_threshold:
            logger.log_policy_retrieval(query, "fallback", best_score)
            duration = time.time() - start_time
            logger.log_agent_complete("policy_retrieval", FALLBACK_POLICY, duration)
            return FALLBACK_POLICY
        
        result = {
            "policy_id": best_policy["id"],
            "title": best_policy["title"],
            "policy_text": best_policy["text"],
            "score": best_score
        }
        
        logger.log_policy_retrieval(query, best_policy["id"], best_score)
        duration = time.time() - start_time
        logger.log_agent_complete("policy_retrieval", result, duration)
        
        return result
        
    except Exception as e:
        error = PolicyException(f"Failed to retrieve policy: {str(e)}")
        logger.log_agent_error("policy_retrieval", error, {"query": query})
        # Return fallback policy on error
        return FALLBACK_POLICY
