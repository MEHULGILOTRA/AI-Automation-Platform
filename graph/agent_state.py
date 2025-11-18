from typing import TypedDict, List, Dict, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Represents the state of our agentic workflow.
    This state is passed between all nodes in the graph.
    """
    query: str
    
    # Agent decisions
    route: str
    
    # Tool outputs
    web_context: Optional[str]
    internal_context: Optional[str]
    email_draft: Optional[str]
    generated_code: Optional[str]
    translation_result: Optional[str]
    
    # Final output
    final_answer: str
    sources: List[Dict[str, str]]
    
    # Conversational Memory
    chat_history: List[BaseMessage]