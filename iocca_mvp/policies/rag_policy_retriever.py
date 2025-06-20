# policies/rag_policy_retriever.py

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
import os

# Load policy documents from file
POLICY_FILE = os.path.join(os.path.dirname(__file__), "policy_docs.json")
with open(POLICY_FILE, "r") as f:
    policy_docs = json.load(f)

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode policy texts
policy_texts = [doc["text"] for doc in policy_docs]
policy_embeddings = model.encode(policy_texts, convert_to_numpy=True)

# RAG-style policy retriever with optional fallback
CONFIDENCE_THRESHOLD = 0.55
FALLBACK_POLICY = {
    "policy_id": "fallback",
    "title": "General Escalation",
    "policy_text": "Situation requires manual review. Escalate to duty manager for case-by-case guidance.",
    "score": 0.0
}

def retrieve_policy(query: str) -> dict:
    query_embedding = model.encode([query], convert_to_numpy=True)
    similarities = cosine_similarity(query_embedding, policy_embeddings)[0]
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])
    best_policy = policy_docs[best_idx]

    if best_score < CONFIDENCE_THRESHOLD:
        return FALLBACK_POLICY

    return {
        "policy_id": best_policy["id"],
        "title": best_policy["title"],
        "policy_text": best_policy["text"],
        "score": best_score
    }
