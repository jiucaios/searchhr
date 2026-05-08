from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List

class AgentState(TypedDict):
    messages: List[str]

def step1(state: AgentState) -> AgentState:
    state["messages"].append("Step 1: Processing...")
    return state

def step2(state: AgentState) -> AgentState:
    state["messages"].append("Step 2: Analyzing...")
    return state

def step3(state: AgentState) -> AgentState:
    state["messages"].append("Step 3: Completing...")
    return state

workflow = StateGraph(AgentState)

workflow.add_node("step1", step1)
workflow.add_node("step2", step2)
workflow.add_node("step3", step3)

workflow.add_edge(START, "step1")
workflow.add_edge("step1", "step2")
workflow.add_edge("step2", "step3")
workflow.add_edge("step3", END)

app = workflow.compile()

result = app.invoke({"messages": ["Start"]})
print("Workflow result:", result)
print("\nLangGraph environment is ready!")