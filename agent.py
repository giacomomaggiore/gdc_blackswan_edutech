from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"

class State(TypedDict):
    user_name: str
    user_context: str
    output: str

graph_builder = StateGraph(State)

llm = init_chat_model("google_genai:gemini-2.0-flash")

def node1(state: State):
    user_name = input("Chi sei: ")
    return {"user_name": user_name}

def node2(state: State):
    user_context = input("In che mondo immaginario vivi: ")
    return {"user_context": user_context}

def node3(state: State):
    print("Scrivo una storia...")
    prompt = f"Scrivi una storia in italiano che abbia come soggetto {state['user_name']} e che sia ambientata in {state['user_context']}"
    
    story = llm.predict(prompt)
    return {"output": story}

# Add nodes to the graph
graph_builder.add_node("node1", node1)
graph_builder.add_node("node2", node2)
graph_builder.add_node("node3", node3)

# Define the flow
graph_builder.add_edge(START, "node1")
graph_builder.add_edge("node1", "node2")
graph_builder.add_edge("node2", "node3")

#compile
graph = graph_builder.compile()

# Test the graph
response = graph.invoke({})
print(response["output"])

