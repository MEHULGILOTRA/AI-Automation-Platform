import os
from dotenv import load_dotenv

# Load .env file variables into environment
load_dotenv()

class Config:
    """Central configuration class."""
    
    # --- Google ---
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set in the .env file.")
        
    # --- Models ---
    ROUTING_MODEL = "gemini-2.5-flash"
    SYNTHESIS_MODEL = "gemini-2.5-flash"
    
    # --- Vector Store ---
    VECTOR_STORE_PATH = "./chroma_db"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # --- LangSmith ---
    LANGCHAIN_API_KEY = os.environ.get("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.environ.get("LANGCHAIN_PROJECT", "AI Agent Platform")
    if LANGCHAIN_API_KEY:
        print(f"[CONFIG] LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")
    else:
        print("[CONFIG] LangSmith tracing is not configured. Set LANGCHAIN_API_KEY to enable.")

# Create a single instance to be imported by other modules
cfg = Config()