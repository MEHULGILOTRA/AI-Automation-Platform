import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from tools.tool_library import web_search_tool, internal_search_tool, generate_and_send_email_tool, code_generator_tool as _code_gen_tool, language_translator_tool as _translator_tool
from graph.agent_state import AgentState
from config import cfg 
import json 
from pydantic import BaseModel, Field
from typing import List

# --- Initialize the LLM ---
llm = ChatGoogleGenerativeAI(
    model=cfg.ROUTING_MODEL, 
    google_api_key=cfg.GOOGLE_API_KEY,
    convert_system_message_to_human=True 
)

# --- Pydantic model for robust routing ---
class Route(BaseModel):
    """Classify the user's query into a specific route."""
    route: str = Field(
        ..., 
        description="The category of the query. Must be one of 'web_research', 'doc_analysis', 'crm_email', 'code_generation' or 'translation'.",
        enum=["web_research", "doc_analysis", "crm_email", "code_generation", "translation"]
    )
llm_with_routing = llm.with_structured_output(Route)

# --- Pydantic model for smart email entity extraction ---
class EmailDetails(BaseModel):
    """Extracts all entities for drafting an email."""
    to_email: str = Field(..., description="The recipient's email address.")
    subject: str = Field(..., description="A concise subject line for the email.")
    body_query: str = Field(..., description="The core request for the email body, e.g., 'a summary of the doc' or 'a follow-up'.")

llm_with_email_details = llm.with_structured_output(EmailDetails)

# --- Helper to format chat history ---
def format_history(history) -> str:
    """
    Robustly formats chat history, handling both LangChain Message Objects 
    AND Python Dictionaries (JSON).
    """
    formatted_messages = []
    
    for msg in history:
        # Case 1: It is a LangChain Object (e.g., HumanMessage)
        if hasattr(msg, 'type'):
            role = msg.type
            content = msg.content
            
        # Case 2: It is a Dictionary (e.g., serialized JSON or Tool Output)
        elif isinstance(msg, dict):
            role = msg.get("type") or msg.get("role", "assistant")
            # Check 'content' first, fall back to 'text' (common in tool outputs)
            content = msg.get("content") or msg.get("text", "")
            
        else:
            continue # Skip unknown formats to prevent crashes

        formatted_messages.append(f"{role.upper()}: {content}")
        
    return "\n".join(formatted_messages)

# --- AGENT NODES ---

def router_agent(state: AgentState) -> dict:
    """
    Planner agent: classifies query and appends to chat history.
    """
    print("Agent Node : Inside Router Agent")
    query = state["query"]
    
    # 1. Append the new user query to the history
    history = state.get("chat_history", [])
    history.append(HumanMessage(content=query))
    
    prompt = f"""
    You are an expert router. Analyze the user's query AND the chat history to classify
    the query into ONE of the following categories:
    
    1. "web_research": For general knowledge questions, news, or public information.
    2. "doc_analysis": For questions about internal documents, summaries, or "what does this doc contain".
    3. "crm_email": For requests to draft emails, follow-ups, or CRM-related tasks.
    4. "code_generation": Requests to write, debug, or explain code/software.
    5. "translation": Requests to translate text from one language to another.
    
    CHAT HISTORY:
    {format_history(history)}

    Most recent QUERY: "{query}"
    """
    
    message = HumanMessage(content=prompt)
    try:
        route_decision = llm_with_routing.invoke([message])
        print(f"Router decision: {route_decision.route}")
        return {"route": route_decision.route, "chat_history": history}
    except Exception as e:
        print(f"Error parsing router decision: {e}. Defaulting to web_research.")
        return {"route": "web_research", "chat_history": history}


def web_research_agent(state: AgentState) -> dict:
    """
    Research Agent: calls web_search_tool.
    """
    print("Agent Node : Inside Web Research Agent")
    query = state["query"]
    results = web_search_tool(query)
    
    return {
        "web_context": results["text"],
        "sources": results["sources"]
    }

def doc_analysis_agent(state: AgentState) -> dict:
    """
    Document Analyst Agent: calls internal_search_tool.
    """
    print("Agent Node : Inside Doc Analysis Agent")
    query = state["query"]
    results = internal_search_tool(query)
    
    return {
        "internal_context": results["text"],
        "sources": results["sources"]
    }

def crm_agent(state: AgentState) -> dict:
    """
    CRM Agent: Extracts entities, gathers context, and SENDS EMAIL DIRECTLY.
    """
    print("Agent Node : Inside CRM Agent")

    query = state["query"]
    history = state.get("chat_history", [])
    
    # 1. Extract Details
    prompt = f"Extract email details from: {query}"
    try:
        details = llm_with_email_details.invoke([HumanMessage(content=prompt)])
    except:
        details = EmailDetails(to_email="unknown", subject="Update", body_query=query)

    # 2. Gather Context
    context_results = internal_search_tool(details.body_query)
    context = context_results.get("text", "")
    
    # 3. CALL THE NEW DIRECT SEND TOOL
    print(f"---CRM Agent: Sending email to {details.to_email}...---")
    results = generate_and_send_email_tool(
        to_email=details.to_email,
        subject=details.subject,
        body_query=details.body_query,
        context=context
    ) 
    
    # 4. Return the "Sent" confirmation as the final answer
    ai_message = AIMessage(content=results["text"])
    history.append(ai_message)
    
    return {
        "email_draft": None,
        "sources": results["sources"],
        "final_answer": results["text"], 
        "chat_history": history 
    }

def synthesis_agent(state: AgentState) -> dict:
    """
    Writing Agent: generates a final report.
    """
    print("Agent Node : Inside Synthesis Agent")
    #print(state)
    query = state["query"]
    history = state.get("chat_history", [])
    print("State is : ", state)

    if state.get("generated_code"):
        print("CODE IS ", state.get("generated_code"))
        return {"final_answer": state["generated_code"], "chat_history": history}

    if state.get("translation_result"):
        print("TRANSLATION IS ", state.get("translation_result"))
        return {"final_answer": state["translation_result"], "chat_history": history}

    if state.get("email_draft"):
        return {}

    context = ""
    if state.get("web_context"):
        context += f"--- WEB SEARCH RESULTS ---\n{state['web_context']}\n"
    if state.get("internal_context"):
        context += f"--- INTERNAL DOCUMENT RESULTS ---\n{state['internal_context']}\n"

    prompt = f"""
    You are an expert synthesis agent.
    Your task is to answer the user's query based on the provided context AND chat history.
    If the query is a follow-up, use the history to understand it.
    
    CHAT HISTORY:
    {format_history(history[:-1])} 

    User Query: "{query}"
    
    Context:
    {context}
    
    Final Answer:
    """
    
    message = HumanMessage(content=prompt)
    response = llm.invoke([message])
    
    # Append AI response to history
    ai_message = AIMessage(content=response.content)
    history.append(ai_message)
    
    return {
        "final_answer": response.content,
        "chat_history": history
    }

def code_generator_tool(state: AgentState):
    """
    Node that handles code generation requests.
    """
    query = state["query"]
    history = state.get("chat_history", [])

    # We pass the whole query as the description. 
    # The tool defaults to Python, but we could extract language if needed.
    print("Agent Node : Inside Code Generator Tool")
    result = _code_gen_tool(description=query, language="Python")
    history.append(result)
    print(result)

    return {
        "generated_code": result["text"],
        "sources": state.get("sources", []) + [{"source": "AI Coder", "link": "Generated"}]
    }

# --- 6. Language Translator Node (Wrapper) ---
def language_translator_tool(state: AgentState):
    """
    Node that handles translation requests.
    We need to figure out the target language from the query before calling the tool.
    """
    print("Agent Node : Inside Language Translator Tool")

    query = state["query"]
    history = state.get("chat_history", [])

    # Helper step: Ask LLM to extract target language and text to clean up input
    extraction_prompt = f"""
    Extract the 'text_to_translate' and 'target_language' from this query: "{query}"
    Return JSON: {{"text": "...", "language": "..."}}
    """
    try:
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        data = json.loads(response.content.replace("```json", "").replace("```", "").strip())
        text_in = data.get("text", query)
        target_lang = data.get("language", "English")
    except:
        text_in = query
        target_lang = "English"

    result = _translator_tool(text=text_in, target_language=target_lang)
    history.append(result)

    print(result)
    return {
        "translation_result": result["text"],
        "sources": state.get("sources", []) + [{"source": "AI Translator", "link": "Generated"}]
    }
