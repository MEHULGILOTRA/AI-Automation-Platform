import os
import requests
import json
import google.generativeai as genai
from typing import List, Dict, Tuple

# --- Config ---
# Read the API key from the environment variable
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY environment variable not set. Please set it before running.")

# --- MODEL DEFINITIONS ---
# Using a single, consistent model name
MODEL_NAME = "gemini-2.5-flash"
RAG_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
SYNTHESIS_MODEL_NAME = f"models/{MODEL_NAME}"

# Configure the simpler SDK for the synthesis step
genai.configure(api_key=API_KEY)


def get_base_model():
    """Returns a standard generative model for synthesis (used in main.py)."""
    return genai.GenerativeModel(model_name=SYNTHESIS_MODEL_NAME)


# --- NEW PLANNER AGENT FUNCTION ---

def get_planner_decision(query: str) -> str:
    """
    Acts as a "Planner Agent" to decide which tool to use.
    Returns 'internal', 'web', or 'both'.
    """
    print(f"Planner Agent is analyzing query: {query}")
    model = get_base_model()
    
    # This prompt forces the LLM to act as a router
    prompt = f"""
    A user is asking a question. Analyze the query and decide the best tool to use.
    Respond with a single word:
    - 'internal' if the query seems to be about internal documents, personal data, or "what does this doc contain".
    - 'web' if the query is a general knowledge question, asking for real-time news, or public information.
    - 'both' if the query is a comparison or requires both internal context and public web context.

    Query: "{query}"
    Decision (internal, web, or both):
    """
    
    try:
        response = model.generate_content(prompt)
        decision = response.text.lower().strip().replace("'", "").replace('"', "")
        
        # Validate the response
        if "internal" in decision:
            print("Planner decision: Use INTERNAL docs")
            return "internal"
        if "web" in decision:
            print("Planner decision: Use WEB search")
            return "web"
        if "both" in decision:
            print("Planner decision: Use BOTH")
            return "both"
        
        print("Planner decision: Fallback to BOTH")
        return "both" # Default fallback
        
    except Exception as e:
        print(f"Error in Planner Agent: {e}. Defaulting to 'both'.")
        return "both"

# --- END NEW FUNCTION ---


def perform_rag_search(query: str) -> Tuple[str, List[Dict]]:
    """
    Performs a RAG query using Google Search via direct HTTP POST.
    This bypasses complex library imports that have been causing errors.
    Returns the generated text and a list of sources.
    """
    print(f"Performing stable HTTP RAG search for: {query}")
    
    system_instruction = (
        "You are an expert AI research assistant. Your job is to answer the "
        "user's query based *only* on the provided search results from the Google Search tool. "
        "Synthesize the information from the search results into a comprehensive, "
        "well-structured report. Do not mention the search results directly."
    )

    # --- BUG FIX ---
    # The payload was malformed. This is the correct structure.
    # "systemInstruction" is a top-level key, not inside "config".
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }
    # --- END BUG FIX ---

    try:
        response = requests.post(
            RAG_API_URL, 
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload)
        )
        response.raise_for_status() # This will raise an HTTPError on 400/500
        result = response.json()
        
        candidate = result.get('candidates', [{}])[0]
        
        # 1. Extract Text
        text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
        
        # 2. Extract Sources
        sources = []
        grounding_metadata = candidate.get('groundingMetadata', {})
        if 'groundingAttributions' in grounding_metadata:
            for attr in grounding_metadata['groundingAttributions']:
                web = attr.get('web')
                if web and web.get('uri') and web.get('title'):
                    sources.append({
                        "uri": web['uri'],
                        "title": web['title'],
                    })
        
        return text, sources

    except requests.exceptions.RequestException as e:
        # This will catch the 400 error and print it
        print(f"HTTP Request Error during RAG search: {e}")
        # We also need to raise it to stop the main.py workflow
        raise e 
    except Exception as e:
        print(f"Unknown error during RAG search: {e}")
        raise e


def generate_text_from_prompt(prompt: str) -> str:
    """
    Generates text from a given prompt using the base SDK model for synthesis.
    """
    print("Synthesizing final answer...")
    model = get_base_model()
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error during text generation: {e}")
        # We also need to raise it to stop the main.py workflow
        raise e