from policy_agent_llm import llm_policy_reason

if __name__ == "__main__":
    query = "Test escalation: No hotels available for crew at ORD."
    context = {"test": True}
    result = llm_policy_reason(query, context)
    print("LLM Decision:", result.get("llm_decision"))
    print("LLM Rationale:", result.get("llm_rationale")) 