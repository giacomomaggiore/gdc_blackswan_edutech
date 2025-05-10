from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import json

# === new langgraph imports ===
from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# === load env & configure Flask ===
load_dotenv('api.env')
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === LLM setup (same Google Gemini) ===
api_key = os.getenv('GEMINI_API_KEY')
llm = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.9, google_api_key=api_key,
                      max_output_tokens=2048, top_p=0.8, top_k=40,
                      convert_system_message_to_human=True)

# === define our State type for the graph ===
class State(TypedDict, total=False):
    user_name: str
    user_context: str
    topic: str
    story: str
    last_chapter: str
    user_answer: str
    output: str
    correct_answer: str
    score: int
    counter: int

# === build the graph ===
graph_builder = StateGraph(State)

# Prompt templates re-used from your new logic:
story_prompt = PromptTemplate(
    input_variables=["user_name","user_context","topic"],
    template=(
        "Inizia a raccontare una storia coinvolgente per bambini o ragazzi in cui il protagonista è {user_name}, "
        "con ambientazione {user_context}. La storia deve essere lunga esattamente 50 parole. "
        "Alla fine del primo capitolo, genera una domanda a risposta multipla sull'argomento {topic}… "
        "OUTPUT in JSON: {{\"story\":\"...\",\"testo_domanda\":\"...\",\"risposte\":{{\"a\":\"...\",\"b\":\"...\",\"c\":\"...\"}},"
        "\"risposta_giusta\":\"...\"}}"
    )
)

follow_up_prompt = PromptTemplate(
    input_variables=["user_name","user_context","topic","last_chapter","user_answer"],
    template=(
        "L'utente ha risposto alla domanda contenuta in {last_chapter} con: \"{user_answer}\". "
        "Valuta e scrivi un nuovo capitolo (max 100 parole)… "
        "OUTPUT in JSON: {{\"story\":\"...\",\"testo_domanda\":\"...\",\"risposte\":{{\"a\":\"...\",\"b\":\"...\",\"c\":\"...\"}},"
        "\"risposta_giusta\":\"...\"}}"
    )
)

# node implementations:
def start_node(state: State) -> State:
    # initialize (taking dynamic overrides from the incoming dict)
    return {
        "user_name": state.get("user_name","adventurer"),
        "user_context": state.get("user_context","fantasy world"),
        "topic":      state.get("topic","algebra"),
        "story": "",
        "last_chapter": "",
        "user_answer": "",
        "output": "",
        "correct_answer": None,
        "score": 0,
        "counter": 0
    }

def story_start(state: State) -> State:
    chain = (
        {"user_name": lambda s: s["user_name"],
         "user_context": lambda s: s["user_context"],
         "topic": lambda s: s["topic"]}
        | story_prompt
        | llm
        | StrOutputParser()
    )
    raw = chain.invoke(state)
    data = json.loads(raw)
    # save for front-end
    return {
        **state,
        "output": data["story"],
        "last_chapter": raw,
        "correct_answer": data["risposta_giusta"]
    }

def question_node(state: State) -> State:
    # front-end will pass "choice" as user_answer
    return {"user_answer": state["user_answer"]}

def follow_up_node(state: State) -> State:
    chain = (
        {"user_name": lambda s: s["user_name"],
         "user_context": lambda s: s["user_context"],
         "topic": lambda s: s["topic"],
         "last_chapter": lambda s: s["last_chapter"],
         "user_answer": lambda s: s["user_answer"]}
        | follow_up_prompt
        | llm
        | StrOutputParser()
    )
    raw = chain.invoke(state)
    data = json.loads(raw)
    return {
        **state,
        "story": state["story"] + "\n" + data["story"],
        "output": data["story"],
        "last_chapter": raw,
        "correct_answer": data["risposta_giusta"]
    }

def check_counter(state: State) -> State:
    return {"counter": state["counter"] + 1}

def end_node(state: State) -> State:
    # nothing special—graph.invoke will return the final state
    return state

def should_continue(state: State) -> bool:
    return state["counter"] < 3

# assemble graph
graph_builder.add_node("start", start_node)
graph_builder.add_node("story_start", story_start)
graph_builder.add_node("question", question_node)
graph_builder.add_node("follow_up", follow_up_node)
graph_builder.add_node("check_counter", check_counter)
graph_builder.add_node("end", end_node)

graph_builder.add_edge(START, "start")
graph_builder.add_edge("start", "story_start")
graph_builder.add_edge("story_start", "question")
graph_builder.add_edge("question", "check_counter")
graph_builder.add_conditional_edges("check_counter", should_continue,
                                    {True: "follow_up", False: "end"})
graph_builder.add_edge("follow_up", "question")

graph = graph_builder.compile()

# === same endpoints, now backed by the graph ===

@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    payload = request.json or {}
    # inject front-end inputs into the initial state
    init = {
        "user_name":    payload.get("character"),
        "user_context": payload.get("storyContext"),
        "topic":        payload.get("mathTopic")
    }
    state = graph.invoke(init)
    return jsonify({
        "sceneText": state["output"],
        "imageRef":  "",
        "progress":  state["counter"] / 5.0,
        "questions": [{
            "prompt": None,    # front-end can re-parse state["last_chapter"]
            "choices": [],     # or you can extract them here if you wish
            "answer": state["correct_answer"],
            "feedback": []
        }],
        "metaphor":    "",
        "mathConcept": "",
        "finished":    state["counter"] >= 3,
        "score":       state["score"]
    })

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    payload = request.json or {}
    state = payload.get("currentScene", {})
    # record the user's choice
    state["user_answer"] = payload.get("choice")
    # advance
    state = graph.invoke(state)
    return jsonify({
        "sceneText": state["output"],
        "imageRef":  "",
        "progress":  state["counter"] / 5.0,
        "questions": [{
            "prompt": None,
            "choices": [],
            "answer": state["correct_answer"],
            "feedback": []
        }],
        "metaphor":    "",
        "mathConcept": "",
        "finished":    state["counter"] >= 3,
        "score":       state["score"]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
