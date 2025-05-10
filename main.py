# Import necessary components
from langgraph.graph import END, StateGraph
from typing import TypedDict, Annotated
from typing_extensions import TypedDict
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Set your Google API key here
GOOGLE_API_KEY = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# List available models
print("Modelli disponibili:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")

# Define the state schema using TypedDict
class State(TypedDict):
    math_topic: str
    story_context: str
    character: str
    story: str
    current_chapter: int
    questions: list
    user_answer: str
    feedback: str
    story_continuation: str
    is_correct: bool
    is_partially_correct: bool

# Initialize the Gemini model
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
    max_output_tokens=2048,
    top_p=0.8,
    top_k=40
)

# Create prompt templates for different stages
story_prompt = ChatPromptTemplate.from_messages([
    ("system", """Sei un narratore creativo ed educatore. Crea una storia breve e coinvolgente che:
    1. Si svolga nel contesto dato
    2. Abbia come protagonista il personaggio scelto
    3. Incorpori naturalmente il concetto matematico nella narrazione
    4. Crei una narrazione ramificata che può cambiare in base alle decisioni del personaggio
    5. Termini con un cliffhanger che porta a una sfida matematica
    
    Regole importanti:
    - La storia deve essere concisa (massimo 200-300 parole)
    - Ogni paragrafo deve essere breve e diretto
    - Usa un linguaggio semplice e chiaro
    - Mantieni la storia coinvolgente ed educativa
    - Fai sentire il lettore come se fosse il personaggio
    
    Scrivi la storia in italiano."""),
    ("user", """Crea una storia breve con questi elementi:
    Argomento Matematico: {math_topic}
    Contesto della Storia: {story_context}
    Personaggio: {character}""")
])

questions_prompt = ChatPromptTemplate.from_messages([
    ("system", """Crea 3 domande interattive che:
    1. Siano direttamente collegate alla storia
    2. Verifichino la comprensione del concetto matematico
    3. Siano coinvolgenti e contestuali
    4. Facciano pensare il lettore come se fosse il personaggio
    5. Abbiano conseguenze chiare per la risposta
    
    Formatta ogni domanda esattamente così:
    Domanda 1: [testo della domanda che fa pensare il lettore come il personaggio]
    Risposta 1: [testo della risposta]
    Conseguenze:
    - Corretta: [cosa succede se la risposta è corretta]
    - Sbagliata: [cosa succede se la risposta è sbagliata]
    
    Domanda 2: [testo della domanda che fa pensare il lettore come il personaggio]
    Risposta 2: [testo della risposta]
    Conseguenze:
    - Corretta: [cosa succede se la risposta è corretta]
    - Sbagliata: [cosa succede se la risposta è sbagliata]
    
    Domanda 3: [testo della domanda che fa pensare il lettore come il personaggio]
    Risposta 3: [testo della risposta]
    Conseguenze:
    - Corretta: [cosa succede se la risposta è corretta]
    - Sbagliata: [cosa succede se la risposta è sbagliata]
    
    Scrivi tutto in italiano."""),
    ("user", """Crea domande basate su:
    Storia: {story}
    Argomento Matematico: {math_topic}
    Personaggio: {character}""")
])

continuation_prompt = ChatPromptTemplate.from_messages([
    ("system", """Sei un narratore creativo. Continua la storia in base alla risposta del personaggio:
    1. Se la risposta è corretta, continua con il miglior esito possibile
    2. Se la risposta è sbagliata, crea una situazione sfidante che il personaggio deve superare
    Mantieni la storia coinvolgente e la personalità del personaggio.
    Scrivi la continuazione in italiano."""),
    ("user", """Continua la storia basandoti su:
    Storia Precedente: {story}
    Domanda: {question}
    Risposta del Personaggio: {user_answer}
    Risposta Corretta: {correct_answer}
    È Corretta: {is_correct}
    Personaggio: {character}
    Argomento Matematico: {math_topic}""")
])

feedback_prompt = ChatPromptTemplate.from_messages([
    ("system", """Sei un tutor di matematica e guida al roleplay. Fornisci un feedback che:
    1. Valuti la correttezza della risposta
    2. Spieghi il concetto matematico se necessario
    3. Incoraggi ulteriori apprendimenti
    4. Mantenga la prospettiva del personaggio
    5. Suggerisca come il personaggio avrebbe potuto approcciare il problema
    Sii incoraggiante ed educativo mantenendo il roleplay coinvolgente.
    Scrivi il feedback in italiano."""),
    ("user", """Fornisci feedback per:
    Domanda: {question}
    Risposta Corretta: {correct_answer}
    Risposta dell'Utente: {user_answer}
    Argomento Matematico: {math_topic}
    Personaggio: {character}""")
])

# Define the node functions
def create_story(state: State) -> State:
    chain = story_prompt | llm | StrOutputParser()
    story = chain.invoke({
        "math_topic": state["math_topic"],
        "story_context": state["story_context"],
        "character": state["character"]
    })
    return {**state, "story": story, "current_chapter": 1}

def generate_questions(state: State) -> State:
    chain = questions_prompt | llm | StrOutputParser()
    questions_text = chain.invoke({
        "story": state["story"],
        "math_topic": state["math_topic"],
        "character": state["character"]
    })
    
    # Parse questions into a list of dictionaries
    questions = []
    current_question = None
    current_answer = None
    current_consequences = {"correct": "", "wrong": ""}
    
    for line in questions_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('Domanda'):
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": current_answer,
                    "consequences": current_consequences
                })
            current_question = line.split(':', 1)[1].strip()
            current_consequences = {"correct": "", "wrong": ""}
        elif line.startswith('Risposta'):
            current_answer = line.split(':', 1)[1].strip()
        elif line.startswith('- Corretta:'):
            current_consequences["correct"] = line.split(':', 1)[1].strip()
        elif line.startswith('- Sbagliata:'):
            current_consequences["wrong"] = line.split(':', 1)[1].strip()
    
    # Add the last question if exists
    if current_question and current_answer:
        questions.append({
            "question": current_question,
            "answer": current_answer,
            "consequences": current_consequences
        })
    
    # Ensure we have at least one question
    if not questions:
        questions = [{
            "question": f"Come {state['character']}, come risolveresti questo problema matematico?",
            "answer": "La soluzione coinvolge " + state["math_topic"],
            "consequences": {
                "correct": "Risolvi con successo il problema e continui il tuo viaggio.",
                "wrong": "Incontri un ostacolo che richiede un approccio diverso."
            }
        }]
    
    return {**state, "questions": questions}

def get_user_answer(state: State) -> State:
    if not state["questions"]:
        print("Errore: Nessuna domanda generata. Uso domanda predefinita.")
        state["questions"] = [{
            "question": f"Come {state['character']}, come risolveresti questo problema matematico?",
            "answer": "La soluzione coinvolge " + state["math_topic"],
            "consequences": {
                "correct": "Risolvi con successo il problema e continui il tuo viaggio.",
                "wrong": "Incontri un ostacolo che richiede un approccio diverso."
            }
        }]
    
    print("\n" + "="*50)
    print("STORY:", state["story"])
    print("="*50)
    print(f"\nCome {state['character']}, devi rispondere a questa domanda:")
    print("\nDOMANDA:", state["questions"][0]["question"])
    print("\nInserisci la tua risposta (come se fossi il personaggio):")
    
    while True:
        try:
            user_answer = input(f"\nRisposta di {state['character']}: ").strip()
            if user_answer:  # Verifica che la risposta non sia vuota
                break
            print("La risposta non può essere vuota. Prova di nuovo.")
        except KeyboardInterrupt:
            print("\nProgramma interrotto dall'utente.")
            exit(0)
    
    return {**state, "user_answer": user_answer}

def evaluate_answer(state: State) -> State:
    # Simple evaluation - in a real application, this would be more sophisticated
    correct_answer = state["questions"][0]["answer"].lower()
    user_answer = state["user_answer"].lower()
    
    # Check if the answer is correct
    is_correct = correct_answer in user_answer or user_answer in correct_answer
    
    return {
        **state,
        "is_correct": is_correct,
        "is_partially_correct": False  # Manteniamo questo campo per compatibilità
    }

def continue_story(state: State) -> State:
    chain = continuation_prompt | llm | StrOutputParser()
    continuation = chain.invoke({
        "story": state["story"],
        "question": state["questions"][0]["question"],
        "user_answer": state["user_answer"],
        "correct_answer": state["questions"][0]["answer"],
        "is_correct": state["is_correct"],
        "character": state["character"],
        "math_topic": state["math_topic"]
    })
    
    # Update the story with the continuation
    new_story = state["story"] + "\n\n" + continuation
    return {**state, "story": new_story, "story_continuation": continuation}

def provide_feedback(state: State) -> State:
    chain = feedback_prompt | llm | StrOutputParser()
    feedback = chain.invoke({
        "question": state["questions"][0]["question"],
        "correct_answer": state["questions"][0]["answer"],
        "user_answer": state["user_answer"],
        "math_topic": state["math_topic"],
        "character": state["character"]
    })
    return {**state, "feedback": feedback}

# Create the graph
graph = StateGraph(State)

# Add nodes
graph.add_node("create_story", create_story)
graph.add_node("generate_questions", generate_questions)
graph.add_node("get_user_answer", get_user_answer)
graph.add_node("evaluate_answer", evaluate_answer)
graph.add_node("continue_story", continue_story)
graph.add_node("provide_feedback", provide_feedback)

# Define the workflow
graph.set_entry_point("create_story")
graph.add_edge("create_story", "generate_questions")
graph.add_edge("generate_questions", "get_user_answer")
graph.add_edge("get_user_answer", "evaluate_answer")
graph.add_edge("evaluate_answer", "continue_story")
graph.add_edge("continue_story", "provide_feedback")
graph.add_edge("provide_feedback", END)

# Compile the graph
app = graph.compile()

# Get user inputs
print("Benvenuto nel Generatore di Storie Matematiche Interattive!")
print("Interpreterai un personaggio in una storia che coinvolge la matematica!")
print("Le tue risposte determineranno come si svilupperà la storia!")
math_topic = input("Inserisci un argomento matematico (es. 'frazioni', 'algebra', 'geometria'): ")
story_context = input("Inserisci un contesto per la storia (es. 'Harry Potter', 'Star Wars'): ")
character = input("Inserisci un personaggio dal contesto (interpreterai questo personaggio): ")

# Execute the workflow
inputs = {
    "math_topic": math_topic,
    "story_context": story_context,
    "character": character
}

result = app.invoke(inputs)

# Print the final feedback
print("\nFeedback:", result["feedback"])
print("\nContinuazione della Storia:", result["story_continuation"])
