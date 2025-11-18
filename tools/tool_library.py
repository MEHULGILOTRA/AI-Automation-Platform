import os
import sys
import requests
import json
from typing import List, Dict, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.messages import HumanMessage 
from config import cfg 
import document_ingestion 

# Add root directory to path to import google_workspace_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_workspace_tools import send_gmail

MODEL_NAME = cfg.SYNTHESIS_MODEL 
API_KEY = cfg.GOOGLE_API_KEY 
RAG_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

llm = ChatGoogleGenerativeAI(
    model=cfg.SYNTHESIS_MODEL,
    google_api_key=cfg.GOOGLE_API_KEY
)

# --- 1. Web Search Tool ---
def web_search_tool(query: str) -> dict:
    print(f"---TOOL: Performing web search for: {query}---")
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": "Summarize search results comprehensively."}]}
    }
    try:
        response = requests.post(
            RAG_API_URL, headers={'Content-Type': 'application/json'}, data=json.dumps(payload)
        )
        response.raise_for_status() 
        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
        sources = []
        if candidate.get('groundingMetadata'):
             for attr in candidate['groundingMetadata'].get('groundingAttributions', []):
                if attr.get('web'): sources.append(attr['web'])
        return {"text": text, "sources": sources}
    except Exception as e:
        return {"text": f"Error: {e}", "sources": []}

# --- 2. Internal Doc Tool ---
def internal_search_tool(query: str) -> dict:
    print(f"---TOOL: Performing internal search for: {query}---")
    doc_chunks = document_ingestion.search_internal_documents(query)
    if not doc_chunks: return {"text": "No info found.", "sources": []}
    return {"text": "\n---\n".join(doc_chunks), "sources": ["Internal Documents"]}

# --- 3. Email Auto-Sender Tool ---
def generate_and_send_email_tool(to_email: str, subject: str, body_query: str, context: str) -> dict:
    print(f"---TOOL: Auto-Sending email to: {to_email}---")
    
    prompt = f"""
    Generate email JSON.
    To: "{to_email}"
    Subject Request: "{subject}"
    Body Request: "{body_query}"
    Context: "{context}"
    Respond ONLY with JSON: {{"to": "...", "subject": "...", "body": "..."}}
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # --- ROBUST CLEANUP LOGIC ---
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        # -----------------------------
        
        email_data = json.loads(content)
        
        send_result = send_gmail(
            email_data.get("to", to_email), 
            email_data.get("subject", subject), 
            email_data.get("body", "")
        )
        
        if send_result.get("success"):
            return {"text": f"✅ Email sent to {email_data.get('to')}!", "sources": ["Gmail API"]}
        return {"text": f"❌ Error: {send_result.get('error')}", "sources": ["Gmail API Error"]}
        
    except Exception as e:
        print(f"Error in generate_and_send_email_tool: {e}")
        return {"text": f"Error: {e}", "sources": []}
import os
import sys
import requests
import json
from typing import List, Dict, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.messages import HumanMessage 
from config import cfg 
import document_ingestion 

# Add root directory to path to import google_workspace_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_workspace_tools import send_gmail

MODEL_NAME = cfg.SYNTHESIS_MODEL 
API_KEY = cfg.GOOGLE_API_KEY 
RAG_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

llm = ChatGoogleGenerativeAI(
    model=cfg.SYNTHESIS_MODEL,
    google_api_key=cfg.GOOGLE_API_KEY
)

# --- 1. Web Search Tool ---
def web_search_tool(query: str) -> dict:
    print(f"---TOOL: Performing web search for: {query}---")
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": "Summarize search results comprehensively."}]}
    }
    try:
        response = requests.post(
            RAG_API_URL, headers={'Content-Type': 'application/json'}, data=json.dumps(payload)
        )
        response.raise_for_status() 
        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
        sources = []
        if candidate.get('groundingMetadata'):
             for attr in candidate['groundingMetadata'].get('groundingAttributions', []):
                if attr.get('web'): sources.append(attr['web'])
        return {"text": text, "sources": sources}
    except Exception as e:
        return {"text": f"Error: {e}", "sources": []}

# --- 2. Internal Doc Tool ---
def internal_search_tool(query: str) -> dict:
    print(f"---TOOL: Performing internal search for: {query}---")
    doc_chunks = document_ingestion.search_internal_documents(query)
    if not doc_chunks: return {"text": "No info found.", "sources": []}
    return {"text": "\n---\n".join(doc_chunks), "sources": ["Internal Documents"]}

# --- 3. Email Auto-Sender Tool ---
def generate_and_send_email_tool(to_email: str, subject: str, body_query: str, context: str) -> dict:
    print(f"---TOOL: Auto-Sending email to: {to_email}---")
    
    prompt = f"""
    Generate email JSON.
    To: "{to_email}"
    Subject Request: "{subject}"
    Body Request: "{body_query}"
    Context: "{context}"
    Respond ONLY with JSON: {{"to": "...", "subject": "...", "body": "..."}}
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # --- ROBUST CLEANUP LOGIC ---
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        # -----------------------------
        
        email_data = json.loads(content)
        
        send_result = send_gmail(
            email_data.get("to", to_email), 
            email_data.get("subject", subject), 
            email_data.get("body", "")
        )
        
        if send_result.get("success"):
            return {"text": f"✅ Email sent to {email_data.get('to')}!", "sources": ["Gmail API"]}
        return {"text": f"❌ Error: {send_result.get('error')}", "sources": ["Gmail API Error"]}
        
    except Exception as e:
        print(f"Error in generate_and_send_email_tool: {e}")
        return {"text": f"Error: {e}", "sources": []}

# --- 4. Code Generator Tool ---
def code_generator_tool(description: str, language: str = "Python") -> dict:
    print(f"---TOOL: Generating {language} code for: {description}---")

    prompt = f"""
    You are an expert software developer.
    Task: Write robust, clean code in {language} for the following requirement.
    Requirement: "{description}"
    
    Output Format:
    1. Provide the code inside a Markdown block (```{language.lower()} ... ```).
    2. Follow with a brief explanation of how the code works.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        print("Generated Code")
        return {"text": response.content, "sources": ["AI Code Generator"]}
    except Exception as e:
        print(f"Error in code_generator_tool: {e}")
        return {"text": f"Error generating code: {e}", "sources": []}

# --- 5. Language Translator Tool ---
def language_translator_tool(text: str, target_language: str) -> dict:
    print(f"---TOOL: Translating text to {target_language}---")

    prompt = f"""
    You are a professional translator.
    Task: Translate the following text into {target_language}.
    
    Text: "{text}"
    
    Constraints:
    - Preserve the original tone and formatting.
    - Return ONLY the translated text, no preamble or explanation.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"text": response.content, "sources": ["AI Translator"]}
    except Exception as e:
        print(f"Error in language_translator_tool: {e}")
        return {"text": f"Error translating text: {e}", "sources": []}