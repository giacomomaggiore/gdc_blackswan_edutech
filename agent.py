from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
import os
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# USER INFO
user_name = "un nago guerriero"
user_context = "mordor del signore degli anelli"
topic = "teorema di pitagora"

os.environ["GOOGLE_API_KEY"] = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"

class State(TypedDict):
    user_name: str
    user_context: str
    topic: str
    story: str
    last_chapter: str
    user_answer: str

graph_builder = StateGraph(State)

llm = init_chat_model("google_genai:gemini-2.0-flash")

# Define the story prompt template
story_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic"],
    template="""Inizia a raccontare una storia coinvolgente per bambini o ragazzi, 
    con ambientazione {user_context}
    La storia deve essere scritta in uno stile narrativo vivo e coinvolgente,
    come se fosse raccontata da un narratore esperto.
    
    Alla fine del primo capitolo, poni all'ascoltatore una domanda a risposta multipla
    con tre risposte riguardo l'argomento {topic} e che aiuti a risolvere il problema
    di quel capitolo.
    
    IMPORTANTE: Dopo le tre opzioni, aggiungi una riga che inizia con "CORRETTA:" 
    seguita dal numero (1, 2 o 3) della risposta corretta.
    
    Il capitolo deve essere lungo 50 parole.
    
    **Obiettivo:** Racconta il primo capitolo, crea suspense, e 
    termina con una chiara domanda matematica legata a ciò che è appena successo.."""
)

follow_up_prompt = PromptTemplate(
    input_variables=["user_name", "user_context", "topic", "last_chapter", "user_answer", "is_correct"],
    template="""L'utente ha risposto alla domanda contenuta in {last_chapter} con: "{user_answer}".
    La risposta è {'corretta' if is_correct else 'non corretta'}.

    {'Se la risposta è corretta, il personaggio deve superare un ostacolo con successo' if is_correct else 'Se la risposta è sbagliata, il personaggio incontra una difficoltà, ma la storia continua comunque, mantenendo un tono costruttivo e motivante'}.

    Scrivi il secondo capitolo della storia (lunghezza: 50 parole), 
    mantenendo lo stesso stile narrativo coinvolgente, l'ambientazione {user_context} 
    e la coerenza con il primo capitolo.

    Alla fine del capitolo, poni **una nuova domanda a risposta multipla** (tre opzioni),
    relativa all'argomento {topic}, che sia utile per superare il nuovo 
    ostacolo o proseguire l'avventura.

    **Obiettivo:** Continua la storia valutando la risposta scrivendo il prossimo 
    capitolo (100 parole max), crea una nuova situazione narrativa interessante, 
    e termina con una nuova domanda matematica coerente."""
)

def node1(state: State):
    state["user_name"] = user_name
    state["user_context"] = user_context
    state["topic"] = topic
    state["story"] = ""
    state["last_chapter"] = ""
    state["user_answer"] = ""
    return state

def node2(state: State):
    # Create chain with the story prompt
    chain = LLMChain(llm=llm, prompt=story_prompt)
    story = chain.run(
        user_name=state["user_name"],
        user_context=state["user_context"],
        topic=state["topic"]
    )
    print("\n=== PRIMO CAPITOLO ===")
    print(story)
    print("=====================\n")
    
    return {"story": story, "last_chapter": story}

def node3(state: State):
    user_answer = input("Quale risposta scegli? ")
    state["user_answer"] = user_answer
    
    # Estrai le opzioni e la risposta corretta dal capitolo precedente
    last_chapter = state["last_chapter"]
    lines = last_chapter.split('\n')
    
    # Trova la riga che indica la risposta corretta
    correct_answer_line = None
    for line in lines:
        if line.strip().startswith("CORRETTA:"):
            correct_answer_line = line.strip()
            break
    
    if correct_answer_line:
        # Estrai il numero della risposta corretta
        correct_option_number = correct_answer_line.split(":")[1].strip()
        
        # Trova l'opzione corrispondente
        correct_option = None
        for line in lines:
            if line.strip().startswith(f"{correct_option_number})"):
                correct_option = line.strip()
                break
        
        # Valuta la risposta
        is_correct = user_answer.strip() == correct_option.strip() if correct_option else False
        
        print("\n=== VALUTAZIONE RISPOSTA ===")
        if is_correct:
            print("✅ Risposta corretta! Procedi con l'avventura...")
        else:
            print("❌ Risposta non corretta. Continua comunque l'avventura...")
            print(f"La risposta corretta era: {correct_option}")
        print("===========================\n")
        
        # Aggiungi il risultato allo stato
        return {
            "user_answer": user_answer,
            "is_correct": is_correct,
            "correct_answer": correct_option
        }
    else:
        print("\n⚠️ Non è stato possibile trovare la risposta corretta nel capitolo.")
        return {
            "user_answer": user_answer,
            "is_correct": False,
            "correct_answer": None
        }

def node4(state: State):
    # Create chain with the follow-up prompt
    chain = LLMChain(llm=llm, prompt=follow_up_prompt)
    story = chain.run(
        user_name=state["user_name"],
        user_context=state["user_context"],
        topic=state["topic"],
        last_chapter=state["last_chapter"],
        user_answer=state["user_answer"],
        is_correct=state["is_correct"]
    )
    print("\n=== SECONDO CAPITOLO ===")
    print(story)
    print("=======================\n")
    
    return {"story": state["story"] + "\n\n" + story, "last_chapter": story}

# Add nodes to the graph
graph_builder.add_node("node1", node1)
graph_builder.add_node("node2", node2)
graph_builder.add_node("node3", node3)
graph_builder.add_node("node4", node4)

# Define the flow
graph_builder.add_edge(START, "node1")
graph_builder.add_edge("node1", "node2")
graph_builder.add_edge("node2", "node3")
graph_builder.add_edge("node3", "node4")

#compile
graph = graph_builder.compile()

# Test the graph
response = graph.invoke({})
print("\n=== STORIA COMPLETA ===")
print(response["story"])
print("=====================\n")

