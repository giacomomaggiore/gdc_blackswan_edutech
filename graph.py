from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
import os
import json
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
#from immgen import generate_image
import datetime

# USER INFO
user_name = "giugiu"
user_context = "la quant più grande del mondo"
topic = "romanzo apocalittico"

os.environ["GOOGLE_API_KEY"] = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"

class State(TypedDict):
    user_name: str
    user_context: str
    topic: str
    story: str
    last_chapter: str
    user_answer: str
    output: str
    correct_answer: str | None
    score: int
    counter: int

graph_builder = StateGraph(State)

llm = init_chat_model("google_genai:gemini-2.0-flash")

# Define the story prompt template - Fixed to remove the problematic JSON formatting in the template
story_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic"],
    template="""Inizia a raccontare una storia coinvolgente per bambini o ragazzi in cui il protagonista è {user_name}, con ambientazione {user_context}.
La storia deve essere scritta in uno stile narrativo vivo e coinvolgente, come se fosse raccontata da un narratore esperto.

La storia deve essere lunga esattamente 50 parole.

Alla fine del primo capitolo, genera una domanda a risposta multipla sull'argomento {topic}, collegata a un ostacolo o problema apparso nel capitolo.

La domanda deve avere tre risposte possibili, identificate come "a", "b", "c".
Indica anche quale tra le tre è la risposta corretta.

**IMPORTANTE:** L'output deve essere restituito in formato JSON con questa struttura esatta:
{{
    "story": "testo della storia di 50 parole",
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
    input_variables=["user_name", "user_context", "topic", "last_chapter", "user_answer"],
    template="""L'utente ha risposto alla domanda contenuta in {last_chapter} con: "{user_answer}".
Valuta se la risposta è corretta tra le tre opzioni proposte nel capitolo precedente.

- Se la risposta è corretta, il personaggio deve superare un ostacolo o avanzare nella storia con successo.
- Se la risposta è sbagliata, il personaggio incontra una difficoltà o deviazione, ma la storia continua comunque, mantenendo un tono costruttivo e motivante.

Scrivi il nuovo capitolo della storia (massimo 100 parole) in cui il protagonista è {user_name}, mantenendo lo stesso stile narrativo coinvolgente, l'ambientazione {user_context}, e la coerenza con il capitolo precedente.
Alla fine del capitolo, poni una nuova domanda a risposta multipla (tre opzioni, identificate come "a", "b", "c"), relativa all'argomento {topic}, utile per superare un ostacolo o far progredire l'avventura.

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

def check_counter(state: State):
    print("counterqqqqqq")
    # Increment the counter
    new_counter = state["counter"] + 1
    
    # Return a dictionary with the updated counter
    return {"counter": new_counter}

#INIZIALIZZA
def start_node(state: State):
    #print("\n=== NODE 1 ===")
    initial_state = {
        "user_name": user_name,
        "user_context": user_context,
        "topic": topic,
        "story": "",
        "last_chapter": "",
        "user_answer": "",
        "score": 0,
        "counter": 0,
    }
    #print(f"Returning state: {initial_state}")
    return initial_state

def story_start(state: State):
    #print("\n=== NODE 2 ===")
    #print(f"Input state: {state}")
    
    # Using the updated LangChain syntax instead of deprecated LLMChain
    chain = (
        {"user_name": lambda x: x["user_name"], 
         "user_context": lambda x: x["user_context"], 
         "topic": lambda x: x["topic"]}
        | story_prompt
        | llm
        | StrOutputParser()
    )
    
    response = chain.invoke(state)
    response = response.replace("```", "")
    response = response.replace("json", "")
    
    try:
        # Parse the JSON response
        story_data = json.loads(response)
        
        # Format the story with the question and answers
        formatted_story = f"""
        === CAPITOLO {state['counter'] + 1} ===
        {story_data["story"]}

        Domanda: {story_data["testo_domanda"]}

        Opzioni:
        a) {story_data["risposte"]["a"]}
        b) {story_data["risposte"]["b"]}
        c) {story_data["risposte"]["c"]}

        Risposta corretta: {story_data["risposta_giusta"]}
        =====================
        """
        print(formatted_story)
        
        return {
            "story": story_data["story"],
            "last_chapter": formatted_story,
            "correct_answer": story_data["risposta_giusta"]
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        #print(f"Raw response: {response}")
        return {
            "story": "Errore nella generazione della storia",
            "last_chapter": "Errore nella generazione della storia",
            "correct_answer": None
        }

#RICHIESTA RISPOSTA
def question_1(state: State):
    #print("\n=== NODE 3 ===")
    #print(f"Input state: {state}")
    user_answer = input("Quale risposta scegli? (a, b, o c): ").lower()
    print(f"User answer: {user_answer}")
    
    if user_answer == state["correct_answer"]:
        print("Risposta corretta!")
        state["score"] += 1
    
    return {"user_answer": user_answer}

def follow_up_1(state: State):
    #print("\n=== NODE 4 ===")
    #print(f"Input state: {state}")
    
    # Using the updated LangChain syntax
    chain = (
        {"user_name": lambda x: x["user_name"], 
         "user_context": lambda x: x["user_context"], 
         "topic": lambda x: x["topic"],
         "last_chapter": lambda x: x["last_chapter"],
         "user_answer": lambda x: x["user_answer"]}
        | follow_up_prompt
        | llm
        | StrOutputParser()
    )
    
    response = chain.invoke(state)
    response = response.replace("```", "")
    response = response.replace("json", "")
    
    try:
        # Parse the JSON response
        story_data = json.loads(response)
        
        # Format the story with the question and answers
        formatted_story = f"""
=== CAPITOLO {state['counter'] + 1} ===
{story_data['story']}

Domanda: {story_data['testo_domanda']}

Opzioni:
a) {story_data['risposte']['a']}
b) {story_data['risposte']['b']}
c) {story_data['risposte']['c']}

Risposta corretta: {story_data['risposta_giusta']}
=======================
"""
        print(formatted_story)
        
        # Ensure we have a string for story concatenation
        previous_story = str(state["story"]) if state["story"] is not None else ""
        new_story = str(story_data['story'])
        
        final_story = f"{previous_story}\n{new_story}".strip()
        
        return {
            "story": final_story,
            "last_chapter": formatted_story,
            "output": story_data['story'],
            "correct_answer": story_data['risposta_giusta']
        }
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Raw response: {response}")
        error_message = "Errore nella generazione della storia"
        previous_story = str(state["story"]) if state["story"] is not None else ""
        return {
            "story": f"{previous_story}\n{error_message}".strip(),
            "last_chapter": error_message,
            "output": error_message,
            "correct_answer": None
        }


def end_story(state: State):
    #print("\n=== END STORY ===")
    print(f"Final state: {state}")
    
    # Return the final story
    
    print("PUNTEGGIO FINALE: ", state["score"])
    return {
        "story": state["story"],
        "last_chapter": state["last_chapter"],
        "output": state["output"]
        
    }

def should_continue(state: State):
    return state["counter"] < 3

# Add nodes to the graph
graph_builder.add_node("start_node", start_node)
graph_builder.add_node("story_start", story_start)
graph_builder.add_node("question_1", question_1)
graph_builder.add_node("follow_up_1", follow_up_1)
graph_builder.add_node("check_counter", check_counter)
graph_builder.add_node("end", end_story)

# Define the flow
graph_builder.add_edge(START, "start_node")
graph_builder.add_edge("start_node", "story_start")
graph_builder.add_edge("story_start", "question_1")
graph_builder.add_edge("question_1", "check_counter")
graph_builder.add_conditional_edges(
    "check_counter",
    should_continue,
    {True: "follow_up_1", False: "end"}
)
graph_builder.add_edge("follow_up_1", "question_1")

# Compile
graph = graph_builder.compile()

# Test the graph
response = graph.invoke({})

print("\n=== STORIA COMPLETA ===")
print(response["story"])
print(response["score"])
print("=====================\n")