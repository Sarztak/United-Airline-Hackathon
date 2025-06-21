from langchain.llms.base import LLM
from langchain.schema import LLMResult
from typing import Any, List, Optional

class DebugLLMWrapper:
    def __init__(self, llm, log_file="llm_prompt_log.txt"):
        self.llm = llm
        self.log_file = log_file

    def invoke(self, input, **kwargs):
        self.log_prompt(input)
        return self.llm.invoke(input, **kwargs)

    async def ainvoke(self, input, **kwargs):
        self.log_prompt(input)
        return await self.llm.ainvoke(input, **kwargs)

    def log_prompt(self, prompt):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("=== RAW PROMPT TEXT ===\n")
            f.write(str(prompt) + "\n")
            f.write("=======================\n\n")


