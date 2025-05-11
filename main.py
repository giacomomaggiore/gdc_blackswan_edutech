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
    template="""Inizia a raccontare una storia coinvolgente per bambini o ragazzi in cui il protagonista è {user_name},
    con ambientazione {user_context}.
    La storia deve essere scritta in uno stile narrativo vivo e coinvolgente, come se fosse raccontata da un narratore esperto.

    La storia deve essere lunga 50-100 parole.

    Alla fine del primo capitolo, genera una domanda a risposta multipla sull'argomento {topic},
    collegata a un ostacolo o problema apparso nel capitolo.

    La domanda deve avere tre risposte possibili, identificate come "a", "b", "c".
    Indica anche quale tra le tre è la risposta corretta.

    **IMPORTANTE:** L'output deve essere restituito in formato JSON con questa struttura esatta:
{{
    "story": "testo della storia",
    "testo_domanda": "testo della domanda generata",
    "risposte": {{
        "a": "testo della risposta a",
        "b": "testo della risposta b",
        "c": "testo della risposta c"
    }},
    "risposta_giusta": "lettera della risposta corretta"
}}

Non inserire spiegazioni né testo extra fuori dal JSON."""
)
follow_up_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic", "user_answer"],
    template="""L'utente ha risposto alla domanda contenuta con {user_answer}".
Valuta se la risposta è corretta tra le tre opzioni proposte nel capitolo precedente.

- Se la risposta è corretta, il personaggio deve superare un ostacolo o avanzare nella storia con successo.
- Se la risposta è sbagliata, il personaggio incontra una difficoltà o deviazione, ma la storia continua 
comunque, mantenendo un tono costruttivo e motivante.

Scrivi il nuovo capitolo della storia (massimo 100 parole) in cui il protagonista è {user_name}, 
mantenendo lo stesso stile narrativo coinvolgente, l'ambientazione {user_context}, e la coerenza con il capitolo precedente.
Alla fine del capitolo, poni una nuova domanda a risposta multipla (tre opzioni, identificate come "a", "b", "c"), relativa
all'argomento {topic}, utile per superare un ostacolo o far progredire l'avventura.

**IMPORTANTE:** L'output deve essere restituito in formato JSON con questa struttura esatta:
{{
"story": "testo del nuovo capitolo della storia (max 100 parole)",
"testo_domanda": "testo della nuova domanda",
"risposte": {{
    "a": "testo della risposta a",
    "b": "testo della risposta b",
    "c": "testo della risposta c"
}},
"risposta_giusta": "lettera della risposta corretta"
}}

Non includere alcun testo o spiegazione al di fuori del JSON."""
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
        state["result"] = "Corretto! Proseguiamo con la storia."
        print("risposta giusta")
    else:
        state["result"] = "Risposta sbagliata! Ma non preoccuparti, la storia continua."
        print("risposta sbagliata")  
          
    state = follow_up(state)
    
    return state

def check_answer(state):
    return state

#controllo counter e finire storia
def check_continue_or_end(state):
    if state.get("counter", 1) >= 5:
        return "end_story"
    else:
        return "wait_for_user"

def should_continue(state):
    return state["counter"] < 3

#fine storia
def end_story(state):
    state["result"] = "Fine dell'avventura! Hai completato tutti i capitoli."
    state["question"] = None
    state["story"] = "🎉 Congratulazioni! Il tuo viaggio si conclude qui. Rileggi l'avventura completa qui sotto."
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