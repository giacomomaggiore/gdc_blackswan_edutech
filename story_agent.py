from typing import TypedDict, Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

# You can set your API key here or pass it to the class
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg")

class StoryState(TypedDict):
    user_name: str
    user_context: str
    topic: str
    story: str
    last_chapter: str
    user_answer: str
    correct_answer: Optional[str]
    score: int
    chapter_number: int

class StoryAgent:
    def __init__(self, api_key: str = None):
        """Initialize the story agent with Google API key."""
        self.api_key = api_key or GOOGLE_API_KEY
        os.environ["GOOGLE_API_KEY"] = self.api_key
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._setup_prompts()
        
    def _setup_prompts(self):
        """Setup the prompt templates for story generation."""
        self.story_prompt = PromptTemplate(
            input_variables=["user_name", "user_context", "topic"],
            template=(
                "Inizia a raccontare una storia coinvolgente per bambini o ragazzi in cui il protagonista è {user_name}, "
                "con ambientazione {user_context}. La storia deve essere scritta in uno stile narrativo vivo e coinvolgente, "
                "come se fosse raccontata da un narratore esperto.\n\n"
                "La storia deve essere lunga esattamente 50 parole.\n\n"
                "Alla fine del primo capitolo, genera una domanda a risposta multipla sull'argomento {topic}, collegata a un ostacolo o problema apparso nel capitolo.\n"
                "La domanda deve avere tre risposte possibili, identificate come 'a', 'b', 'c'. Indica anche quale tra le tre è la risposta corretta.\n\n"
                "Scrivi tutto in linguaggio naturale, senza alcuna formattazione JSON o codice.\n"
                "Esempio di output atteso:\n"
                "---\n"
                "[Storia di 50 parole]\n\n"
                "Domanda: [testo della domanda]\n"
                "a) [testo risposta a]\n"
                "b) [testo risposta b]\n"
                "c) [testo risposta c]\n"
                "Risposta corretta: [lettera corretta]\n"
                "---"
            )
        )

        self.follow_up_prompt = PromptTemplate(
            input_variables=["user_name", "user_context", "topic", "last_chapter", "user_answer"],
            template=(
                "L'utente ha risposto alla domanda contenuta in questo capitolo: {last_chapter} con: '{user_answer}'.\n"
                "Valuta se la risposta è corretta tra le tre opzioni proposte nel capitolo precedente.\n"
                "- Se la risposta è corretta, il personaggio deve superare un ostacolo o avanzare nella storia con successo.\n"
                "- Se la risposta è sbagliata, il personaggio incontra una difficoltà o deviazione, ma la storia continua comunque, mantenendo un tono costruttivo e motivante.\n\n"
                "Scrivi il nuovo capitolo della storia (massimo 100 parole) in cui il protagonista è {user_name}, mantenendo lo stesso stile narrativo coinvolgente, l'ambientazione {user_context}, e la coerenza con il capitolo precedente.\n"
                "Alla fine del capitolo, poni una nuova domanda a risposta multipla (tre opzioni, identificate come 'a', 'b', 'c'), relativa all'argomento {topic}, utile per superare un ostacolo o far progredire l'avventura.\n"
                "Indica anche quale tra le tre è la risposta corretta.\n\n"
                "Scrivi tutto in linguaggio naturale, senza alcuna formattazione JSON o codice.\n"
                "Esempio di output atteso:\n"
                "---\n"
                "[Nuovo capitolo della storia]\n\n"
                "Domanda: [testo della domanda]\n"
                "a) [testo risposta a]\n"
                "b) [testo risposta b]\n"
                "c) [testo risposta c]\n"
                "Risposta corretta: [lettera corretta]\n"
                "---"
            )
        )

    def start_story(self, user_name: str, user_context: str, topic: str) -> Dict[str, Any]:
        """Start a new story with initial parameters."""
        initial_state = {
            "user_name": user_name,
            "user_context": user_context,
            "topic": topic,
            "story": "",
            "last_chapter": "",
            "user_answer": "",
            "correct_answer": None,
            "score": 0,
            "chapter_number": 1
        }
        
        # Generate first chapter
        chain = (
            {"user_name": lambda x: x["user_name"], 
             "user_context": lambda x: x["user_context"], 
             "topic": lambda x: x["topic"]}
            | self.story_prompt
            | self.llm
            | StrOutputParser()
        )
        
        response = chain.invoke(initial_state)
        formatted_story, correct_answer = self._extract_chapter_and_answer(response)
        
        # Update state
        initial_state.update({
            "story": response.strip(),
            "last_chapter": formatted_story,
            "correct_answer": correct_answer
        })
        
        return initial_state

    def process_answer(self, state: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Process user's answer and generate next chapter."""
        # Update state with user's answer
        state["user_answer"] = user_answer.lower()
        
        # Check if answer is correct
        if state["user_answer"] == state["correct_answer"]:
            state["score"] += 1
        
        # Generate next chapter
        chain = (
            {"user_name": lambda x: x["user_name"], 
             "user_context": lambda x: x["user_context"], 
             "topic": lambda x: x["topic"],
             "last_chapter": lambda x: x["last_chapter"],
             "user_answer": lambda x: x["user_answer"]}
            | self.follow_up_prompt
            | self.llm
            | StrOutputParser()
        )
        
        response = chain.invoke(state)
        state["chapter_number"] += 1
        formatted_story, correct_answer = self._extract_chapter_and_answer(response)
        
        # Update state with new chapter
        state.update({
            "story": f"{state['story']}\n{response.strip()}",
            "last_chapter": formatted_story,
            "correct_answer": correct_answer
        })
        
        return state

    def _extract_chapter_and_answer(self, text: str):
        """
        Extract the formatted chapter and the correct answer letter from the model's output.
        """
        # Try to extract the answer letter from the output
        correct_answer = None
        lines = text.splitlines()
        for line in lines:
            if line.lower().startswith("risposta corretta:"):
                correct_answer = line.split(":", 1)[-1].strip().lower()
        return text.strip(), correct_answer 