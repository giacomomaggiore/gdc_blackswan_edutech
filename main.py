from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from graph import graph  # importa il graph dal tuo file (rinominalo se necessario)

app = FastAPI()

# Stato persistente in memoria (esempio semplice)
current_state: Dict[str, Any] = {}

class UserInput(BaseModel):
    user_answer: Optional[str] = ""
    user_name: Optional[str] = "un nago guerriero"
    user_context: Optional[str] = "mordor del signore degli anelli"
    topic: Optional[str] = "teorema di pitagora"

@app.get("/state")
def get_state():
    return current_state or {"message": "Nessuno stato attivo. Avvia la storia."}

@app.post("/start")
def start_story(user_input: UserInput):
    # Lancia il grafo da capo con i parametri iniziali (override se specificati)
    global current_state
    current_state = {
        "user_name": user_input.user_name,
        "user_context": user_input.user_context,
        "topic": user_input.topic,
        "story": "",
        "last_chapter": "",
        "user_answer": "",
        "score": 0,
        "counter": 0
    }
    output = graph.invoke(current_state)
    current_state.update(output)
    return current_state

@app.post("/answer")
def answer_question(answer: str = Body(..., embed=True)):
    global current_state
    if not current_state:
        return {"error": "Nessuna storia attiva. Usa /start per iniziare."}
    current_state["user_answer"] = answer.lower()
    output = graph.invoke(current_state)
    current_state.update(output)
    return current_state