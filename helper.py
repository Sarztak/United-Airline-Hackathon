from langchain_openai import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from debug_llm import DebugLLMWrapper
from dotenv import load_dotenv

def load_llm(service, model, temperature=0, debug=False):
    assert service in ["gemini", "openai"]
    if service == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model, 
            temperature=temperature,
        )
    elif service == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        llm = OpenAI(
            openai_api_key=api_key,
            model=model,
            temperature=temperature,
        )
    
    # if debug:
    #     llm = DebugLLMWrapper(llm)
    
    return llm 

if __name__ == "__main__":
    load_dotenv()
    llm = load_llm(service="openai", model="gpt-o4-mini", debug=True)
