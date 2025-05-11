from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph
import uuid
from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
import os
import json
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import requests

story_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic"],
    template="""Start telling an engaging story for children or young people where the protagonist is {user_name},
    set in {user_context}.
    The story should be written in a lively and engaging narrative style, as if told by an experienced narrator.

    The story should be 50-100 words long.

    At the end of the first chapter, generate a multiple-choice question about the topic {topic},
    connected to an obstacle or problem that appeared in the chapter.

    The question must have three possible answers, identified as "a", "b", "c".
    Also indicate which of the three is the correct answer.

    **IMPORTANT:** The output must be returned in JSON format with this exact structure:
{{
    "story": "story text",
    "testo_domanda": "generated question text",
    "risposte": {{
        "a": "answer a text",
        "b": "answer b text",
        "c": "answer c text"
    }},
    "risposta_giusta": "letter of the correct answer"
}}

Do not include any explanations or extra text outside the JSON."""
)
follow_up_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic", "user_answer"],
    template="""The user answered the question with {user_answer}".
Evaluate whether the answer is correct among the three options proposed in the previous chapter.

- If the answer is correct, the character should overcome an obstacle or successfully advance in the story.
- If the answer is wrong, the character encounters a difficulty or deviation, but the story continues
anyway, maintaining a constructive and motivating tone.

Write the new chapter of the story (maximum 100 words) in which the protagonist is {user_name},
keeping the same engaging narrative style, the setting {user_context}, and consistency with the previous chapter.
At the end of the chapter, ask a new multiple-choice question (three options, identified as "a", "b", "c"), related
to the topic {topic}, useful for overcoming an obstacle or advancing the adventure.

**IMPORTANT:** The output must be returned in JSON format with this exact structure:
{{
"story": "text of the new chapter of the story (max 100 words)",
"testo_domanda": "text of the new question",
"risposte": {{
    "a": "text of answer a",
    "b": "text of answer b",
    "c": "text of answer c"
}},
"risposta_giusta": "letter of the correct answer"
}}

Do not include any text or explanation outside the JSON."""
)
app = FastAPI()
os.environ["GOOGLE_API_KEY"] = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"


llm = init_chat_model("google_genai:gemini-2.0-flash")


# CORS per permettere chiamate da React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:3000"],

    allow_methods=["*"],
    allow_headers=["*"],
)

# Stato simulato in memoria (usa Redis o DB in produzione)
session_store = {}

# LangGraph nodes
def ask_question(state):
    
    chain = (
        story_prompt
        | llm
        | StrOutputParser()
    )
    
    response = chain.invoke(state)
    response = response.replace("```", "")
    response = response.replace("json", "")
    story_data = json.loads(response)
    
    state["story"] = story_data["story"]
    #INIZIALIZZAZIONE STORIA C0MPOLETA
    state["full_story"] = story_data["story"]
    
    state["counter"] = 1
    
    state["question"] = story_data["testo_domanda"]
    state["answer_1"] = story_data["risposte"]["a"]
    state["answer_2"] = story_data["risposte"]["b"]
    state["answer_3"] = story_data["risposte"]["c"]
    
    state["correct_answer"] = story_data["risposta_giusta"]
    
    return state

def follow_up(state):
    print(state["counter"])
    print("follow up!!!")
    
    chain = (
        follow_up_prompt
        | llm
        | StrOutputParser()
    )
    state["user_answer"] = state.get("user_answer", "")
    response = chain.invoke(state)
    response = response.replace("```", "")
    response = response.replace("json", "")
    story_data = json.loads(response)
    
    state["story"] = story_data["story"]
    
    state["question"] = story_data["testo_domanda"]
    state["answer_1"] = story_data["risposte"]["a"]
    state["answer_2"] = story_data["risposte"]["b"]
    state["answer_3"] = story_data["risposte"]["c"]
    
    state["correct_answer"] = story_data["risposta_giusta"]
    
    #AGGIUNTA NUOVO CAPITOLO ALLA STORIA C0MPLETA
    nuovo_paragrafo = story_data["story"]
    state["story"] = nuovo_paragrafo

    if "full_story" not in state:
        state["full_story"] = nuovo_paragrafo
    else:
        state["full_story"] += "\n\n" + nuovo_paragrafo

    
    #UPDATE COUNTER CAPITOLI
    state["counter"] += 1   # ✅ incrementa
    
    
    return state

def wait_for_user(state):
    print("wait_for_user")
    if state.get("user_answer") == state.get("correct_answer"):
        state["result"] = "Correct! Let's continue with the story."
        print("correct answer")
    else:
        state["result"] = "Wrong answer! But don't worry, the story continues."
        print("wrong answer")  
          
    state = follow_up(state)
    
    return state

def check_answer(state):
    return state

#check counter and end story
def check_continue_or_end(state):
    if state.get("counter", 1) >= 5:
        return "end_story"
    else:
        return "wait_for_user"

def should_continue(state):
    return state["counter"] < 3

#end story
def end_story(state):
    state["result"] = "End of the adventure! You have completed all chapters."
    state["question"] = None
    state["story"] = "🎉 Congratulations! Your journey ends here. Re-read the complete adventure below."
    return state

# Costruzione del grafo
builder = StateGraph(dict)
builder.add_node("ask_question", ask_question)
builder.add_node("wait_for_user", wait_for_user)
builder.add_node("check_answer", check_answer)


builder.add_node("check_continue_or_end", check_continue_or_end)
builder.add_node("end_story", end_story)

builder.set_entry_point("ask_question")
builder.add_edge("ask_question", "wait_for_user")

builder.add_conditional_edges(
    "wait_for_user",
    should_continue,
    {
        True: "check_answer",  # (loop)
        False: "end_story"           # (stop)
    }
)

graph = builder.compile() 

@app.post("/start")
async def start(request: Request):
    data = await request.json()
    
    session_id = data.get("session_id") or str(uuid.uuid4())  
    
    context = data.get("context")
    username = data.get("username")
    
    print("context", context, username)
    state = {"user_name": username, "user_context": context, "topic": "teorema di pitagora", "session_id" : session_id}
  
    response = graph.invoke(state)
    session_store[session_id] = response
    
    return {
        "session_id": session_id,
        "story": response.get("story"),   
        "full_story": response.get("full_story"),
        "question": response.get("question"),
        "answers": {
            "a": response.get("answer_1"),
            "b": response.get("answer_2"),
            "c": response.get("answer_3")
        },
        "correct": response.get("correct_answer"),
        "counter": response.get("counter")
    }
    
    
    
@app.post("/continue")
async def continue_graph(request: Request):
    data = await request.json()
    session_id = data["session_id"]
    user_answer = data["user_answer"]

    state = session_store.get(session_id)
    if not state:
        return {"error": "Sessione non trovata"}

    state["user_answer"] = user_answer
    
    result = graph.invoke(state)
    session_store[session_id] = result

    return {
        "result": result.get("result"),
        "story": result.get("story"),
        "full_story": result.get("full_story"),
        "question": result.get("question"),
        "counter": result.get("counter"),
        
        "answers": {
            "a": result.get("answer_1"),
            "b": result.get("answer_2"),
            "c": result.get("answer_3")
        },
        
        "correct": result.get("correct_answer")
    }