import os
import openai
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from dotenv import load_dotenv

from config import config
from utils.logger import get_agent_logger
from utils.exceptions import ExternalAPIException, ConfigurationException

load_dotenv()

# Set up logging
logger = get_agent_logger("policy_agent_llm")

async def llm_policy_reason_stream(query: str, context: Optional[Dict[str, Any]] = None, 
                                  stream_callback: Optional[Callable] = None) -> Dict[str, str]:
    """
    Uses GPT-4.0 to reason over escalation policy with token streaming.
    Args:
        query (str): Situation or escalation description.
        context (dict, optional): Additional context for the LLM.
        stream_callback: Callback function to handle streaming tokens
    Returns:
        dict: {
            'llm_decision': str,
            'llm_rationale': str,
            'stream_id': str
        }
    """
    start_time = time.time()
    stream_id = str(uuid.uuid4())
    
    logger.log_agent_start("llm_policy_reasoning_stream", {
        "query": query,
        "context": context,
        "stream_id": stream_id
    })
    
    # Validate configuration
    if not config.openai.api_key or config.openai.api_key == 'YOUR_OPENAI_API_KEY':
        logger.log_agent_error("llm_policy_reasoning_stream", 
            ConfigurationException("OpenAI API key not configured"), 
            {"query": query}
        )
        # Mock response if API key is not set
        mock_response = {
            'llm_decision': 'Escalate to duty manager for manual review.',
            'llm_rationale': f"[MOCK] Based on the query '{query}', manual escalation is recommended.",
            'stream_id': stream_id
        }
        if stream_callback:
            await stream_callback({
                'type': 'reasoning_complete',
                'content': mock_response['llm_rationale'],
                'stream_id': stream_id
            })
        return mock_response
    
    # Prepare structured prompt for reasoning
    structured_prompt = f"""You are an airline operations escalation policy expert. Analyze the following situation and provide detailed, step-by-step reasoning.

SITUATION: {query}
CONTEXT: {context if context else 'No additional context provided'}

Please provide your analysis in the following structured format:

1. SITUATION ANALYSIS:
   - What is the core problem?
   - What are the key constraints and factors?

2. POLICY CONSIDERATIONS:
   - Which airline policies apply to this situation?
   - What are the regulatory requirements?

3. OPTIONS EVALUATION:
   - What are the possible courses of action?
   - What are the pros and cons of each option?

4. DECISION RATIONALE:
   - What is your recommended action?
   - Why is this the best option?

Please think through each step carefully and show your reasoning process."""
    
    try:
        client = openai.OpenAI(api_key=config.openai.api_key)
        
        logger.log_llm_stream_start(config.openai.model, structured_prompt, stream_id)
        
        # Start streaming
        full_response = ""
        token_count = 0
        
        stream = client.chat.completions.create(
            model=config.openai.model,
            messages=[
                {"role": "system", "content": "You are an expert airline operations analyst. Think step-by-step and show your reasoning process clearly."},
                {"role": "user", "content": structured_prompt}
            ],
            max_tokens=config.openai.max_tokens * 4,  # Allow more tokens for detailed reasoning
            temperature=config.openai.temperature,
            stream=config.openai.stream
        )
        
        current_section = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                full_response += token
                token_count += 1
                
                # Log individual token if debug level
                logger.log_llm_token(stream_id, token, token_count)
                
                # Detect reasoning sections for structured streaming
                if "SITUATION ANALYSIS:" in token:
                    current_section = "situation_analysis"
                    if stream_callback:
                        await stream_callback({
                            'type': 'reasoning_step',
                            'step': 'situation_analysis',
                            'content': 'Analyzing the situation...',
                            'stream_id': stream_id
                        })
                elif "POLICY CONSIDERATIONS:" in token:
                    current_section = "policy_considerations"
                    if stream_callback:
                        await stream_callback({
                            'type': 'reasoning_step',
                            'step': 'policy_considerations',
                            'content': 'Reviewing applicable policies...',
                            'stream_id': stream_id
                        })
                elif "OPTIONS EVALUATION:" in token:
                    current_section = "options_evaluation"
                    if stream_callback:
                        await stream_callback({
                            'type': 'reasoning_step',
                            'step': 'options_evaluation',
                            'content': 'Evaluating possible options...',
                            'stream_id': stream_id
                        })
                elif "DECISION RATIONALE:" in token:
                    current_section = "decision_rationale"
                    if stream_callback:
                        await stream_callback({
                            'type': 'reasoning_step',
                            'step': 'decision_rationale',
                            'content': 'Making final recommendation...',
                            'stream_id': stream_id
                        })
                
                # Stream individual tokens to callback
                if stream_callback:
                    await stream_callback({
                        'type': 'token',
                        'content': token,
                        'section': current_section,
                        'stream_id': stream_id
                    })
                
                # Add small delay for realistic streaming effect
                if config.openai.stream_delay_ms > 0:
                    await asyncio.sleep(config.openai.stream_delay_ms / 1000.0)
        
        duration = time.time() - start_time
        logger.log_llm_stream_complete(stream_id, full_response, token_count, duration)
        
        # Extract decision from the structured response
        lines = full_response.split('\n')
        decision_section = False
        decision_lines = []
        
        for line in lines:
            if "DECISION RATIONALE:" in line or decision_section:
                decision_section = True
                if line.strip() and not "DECISION RATIONALE:" in line:
                    decision_lines.append(line.strip())
        
        decision = decision_lines[0] if decision_lines else "Escalate to duty manager for manual review."
        
        result = {
            'llm_decision': decision,
            'llm_rationale': full_response,
            'stream_id': stream_id
        }
        
        # Notify callback of completion
        if stream_callback:
            await stream_callback({
                'type': 'reasoning_complete',
                'content': full_response,
                'decision': decision,
                'stream_id': stream_id
            })
        
        logger.log_agent_complete("llm_policy_reasoning_stream", result, duration)
        return result
        
    except openai.APIError as e:
        error = ExternalAPIException(f"OpenAI API error: {str(e)}", "OPENAI_API_ERROR")
        logger.log_agent_error("llm_policy_reasoning_stream", error, {"query": query})
        result = {
            'llm_decision': 'Error during LLM call - escalate to duty manager.',
            'llm_rationale': f"OpenAI API error: {str(e)}",
            'stream_id': stream_id
        }
        if stream_callback:
            await stream_callback({
                'type': 'error',
                'content': f"API Error: {str(e)}",
                'stream_id': stream_id
            })
        return result
    except Exception as e:
        error = ExternalAPIException(f"Unexpected error during LLM call: {str(e)}", "UNEXPECTED_ERROR")
        logger.log_agent_error("llm_policy_reasoning_stream", error, {"query": query})
        result = {
            'llm_decision': 'Error during LLM call - escalate to duty manager.',
            'llm_rationale': f"Unexpected error: {str(e)}",
            'stream_id': stream_id
        }
        if stream_callback:
            await stream_callback({
                'type': 'error',
                'content': f"Unexpected error: {str(e)}",
                'stream_id': stream_id
            })
        return result

def llm_policy_reason(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
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
    start_time = time.time()
    
    logger.log_agent_start("llm_policy_reasoning", {
        "query": query,
        "context": context
    })
    
    # Validate configuration
    if not config.openai.api_key or config.openai.api_key == 'YOUR_OPENAI_API_KEY':
        logger.log_agent_error("llm_policy_reasoning", 
            ConfigurationException("OpenAI API key not configured"), 
            {"query": query}
        )
        # Mock response if API key is not set
        return {
            'llm_decision': 'Escalate to duty manager for manual review.',
            'llm_rationale': f"[MOCK] Based on the query '{query}', manual escalation is recommended."
        }
    
    # Prepare prompt
    prompt = f"Situation: {query}\nContext: {context}\nWhat is the recommended escalation action? Explain your reasoning."
    
    try:
        client = openai.OpenAI(api_key=config.openai.api_key)
        
        response = client.chat.completions.create(
            model=config.openai.model,
            messages=[
                {"role": "system", "content": "You are an airline operations escalation policy expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.openai.max_tokens,
            temperature=config.openai.temperature
        )
        
        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        # Log successful LLM call
        logger.log_llm_call(
            model=config.openai.model,
            prompt=prompt,
            response=answer,
            tokens_used=tokens_used
        )
        
        result = {
            'llm_decision': answer.split('\n')[0],
            'llm_rationale': answer
        }
        
        duration = time.time() - start_time
        logger.log_agent_complete("llm_policy_reasoning", result, duration)
        
        return result
        
    except openai.APIError as e:
        error = ExternalAPIException(f"OpenAI API error: {str(e)}", "OPENAI_API_ERROR")
        logger.log_agent_error("llm_policy_reasoning", error, {"query": query})
        return {
            'llm_decision': 'Error during LLM call - escalate to duty manager.',
            'llm_rationale': f"OpenAI API error: {str(e)}"
        }
    except Exception as e:
        error = ExternalAPIException(f"Unexpected error during LLM call: {str(e)}", "UNEXPECTED_ERROR")
        logger.log_agent_error("llm_policy_reasoning", error, {"query": query})
        return {
            'llm_decision': 'Error during LLM call - escalate to duty manager.',
            'llm_rationale': f"Unexpected error: {str(e)}"
        } 