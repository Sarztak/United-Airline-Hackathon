import os
import openai
import re
from dotenv import load_dotenv

load_dotenv()

# Set your OpenAI API key here or via environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

def llm_policy_reason(query, context=None):
    """
    Uses GPT-4.0 to reason over escalation policy.
    Args:
        query (str): Situation or escalation description.
        context (dict, optional): Additional context for the LLM.
    Returns:
        dict: {
            'llm_decision': str,
            'llm_rationale': str
        }
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'YOUR_OPENAI_API_KEY':
        # Mock response if API key is not set
        return {
            'llm_decision': 'Escalate to duty manager for manual review.',
            'llm_rationale': f"[MOCK] Based on the query '{query}', manual escalation is recommended."
        }
    prompt = f"Situation: {query}\nContext: {context}\nWhat is the recommended escalation action? Explain your reasoning."
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an airline operations escalation policy expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=256,
            temperature=0.2
        )
        answer = response.choices[0].message.content
        return {
            'llm_decision': answer.split('\n')[0],
            'llm_rationale': answer
        }
    except Exception as e:
        return {
            'llm_decision': 'Error during LLM call.',
            'llm_rationale': str(e)
        } 