from langgraph.graph import StateGraph, END
from graph.agent_state import AgentState
from graph.agent_nodes import (
    router_agent,
    web_research_agent,
    doc_analysis_agent,
    crm_agent,
    synthesis_agent,
    code_generator_tool,
    language_translator_tool
)

def decide_next_node(state: AgentState) -> str:
    """
    Conditional logic for the graph.
    Based on the router's decision, pick the next agent.
    """
    print(f"---ROUTING: Decision is '{state['route']}'---")
    # The router_agent's output (e.g., "crm_email")
    # will be used directly as the key for the conditional map.
    return state["route"]

# --- Define the Graph ---

workflow = StateGraph(AgentState)

# 1. Add Nodes
workflow.add_node("router_agent", router_agent)
workflow.add_node("web_research_agent", web_research_agent)
workflow.add_node("doc_analysis_agent", doc_analysis_agent)
workflow.add_node("crm_agent", crm_agent)
workflow.add_node("synthesis_agent", synthesis_agent)
workflow.add_node("code_generator_tool", code_generator_tool)
workflow.add_node("language_translator_tool", language_translator_tool)

# 2. Define Edges

# Start with the router
workflow.set_entry_point("router_agent")

# Add the conditional edges from the router
workflow.add_conditional_edges(
    "router_agent",
    decide_next_node,
    {
        "web_research": "web_research_agent",
        "doc_analysis": "doc_analysis_agent",
        "crm_email": "crm_agent",
        "code_generation" : "code_generator_tool",
        "translation" : "language_translator_tool",
    }
)

# The specialist agents all route to the synthesizer
workflow.add_edge("web_research_agent", "synthesis_agent")
workflow.add_edge("doc_analysis_agent", "synthesis_agent")
workflow.add_edge("code_generator_tool", "synthesis_agent")
workflow.add_edge("language_translator_tool", "synthesis_agent")
# The CRM agent can go straight to the end
workflow.add_edge("crm_agent", END) 

# The synthesizer is the final step
workflow.add_edge("synthesis_agent", END)

# 3. Compile the graph
app = workflow.compile()

print("--- Agentic Workflow Compiled (Stateless / Manual Memory) ---")