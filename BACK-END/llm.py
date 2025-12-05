# llm.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Instância que será criada APENAS uma vez
_llm_instance = None


def get_llm():
    """
    Retorna a instância global do LLM.
    Se ainda não existir, cria. (Singleton simples)
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            google_api_key=GOOGLE_API_KEY
        )
    return _llm_instance
