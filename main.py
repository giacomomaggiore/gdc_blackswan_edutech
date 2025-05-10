from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uuid

from langgraph.graph import StateGraph, START
from graph import graph  # <--- metti qui il tuo codice o importalo correttamente

app = FastAPI(title="Story Quiz API")

# In-memory session store (per demo)
sessions: Dict[str, dict] = {}

# === MODELS ===

class NewSessionRequest(BaseModel):
    pass  # puoi eventualmente accettare user_name, topic, ecc.

class AnswerRequest(BaseModel):
    session_id: str
    answer: str  # a, b, c

class SessionStateResponse(BaseModel):
    session_id: str
    story: str
    last_chapter: str
    score: int
    counter: int


# === ROUTES ===

@app.post("/start", response_model=SessionStateResponse)
def start_story(_: NewSessionRequest):
    session_id = str(uuid.uuid4())
    state = graph.invoke({})
    sessions[session_id] = state

    return SessionStateResponse(
        session_id=session_id,
        story=state["story"],
        last_chapter=state["last_chapter"],
        score=state["score"],
        counter=state["counter"]
    )


@app.post("/answer", response_model=SessionStateResponse)
def submit_answer(req: AnswerRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[req.session_id]

    # Simula l’inserimento della risposta e prosegui nel grafo
    state["user_answer"] = req.answer.lower()
    if state["user_answer"] == state.get("correct_answer"):
        state["score"] += 1

    state["counter"] += 1

    if state["counter"] < 3:
        # Continua con il prossimo capitolo
        updated_state = graph.invoke(state)
    else:
        # Fine della storia
        updated_state = graph.invoke(state)

    sessions[req.session_id] = updated_state

    return SessionStateResponse(
        session_id=req.session_id,
        story=updated_state["story"],
        last_chapter=updated_state["last_chapter"],
        score=updated_state["score"],
        counter=updated_state["counter"]
    )


@app.get("/state/{session_id}", response_model=SessionStateResponse)
def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    state = sessions[session_id]
    return SessionStateResponse(
        session_id=session_id,
        story=state["story"],
        last_chapter=state["last_chapter"],
        score=state["score"],
        counter=state["counter"]
    )