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
print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")

# Define the state schema using TypedDict
class State(TypedDict):
    math_topic: str
    story_context: str
    character: str
    story: str
    questions: list
    user_answer: str
    feedback: str

# Initialize the Gemini model
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",  # Updated model name with full path
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
    max_output_tokens=2048,
    top_p=0.8,
    top_k=40
)

# Create prompt templates for different stages
story_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a creative storyteller and educator. Create an engaging story that:
    1. Takes place in the given context
    2. Features the chosen character as the protagonist
    3. Incorporates the mathematical concept naturally into the narrative
    4. Makes the character face challenges related to the math topic
    Keep the story engaging and educational."""),
    ("user", """Create a story with these elements:
    Math Topic: {math_topic}
    Story Context: {story_context}
    Character: {character}""")
])

questions_prompt = ChatPromptTemplate.from_messages([
    ("system", """Create 3 interactive questions that:
    1. Are directly related to the story
    2. Test understanding of the mathematical concept
    3. Are engaging and contextual
    Format each question exactly like this:
    Question 1: [question text]
    Answer 1: [answer text]
    
    Question 2: [question text]
    Answer 2: [answer text]
    
    Question 3: [question text]
    Answer 3: [answer text]"""),
    ("user", """Create questions based on:
    Story: {story}
    Math Topic: {math_topic}""")
])

feedback_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful math tutor. Provide feedback that:
    1. Evaluates the answer's correctness
    2. Explains the mathematical concept if needed
    3. Encourages further learning
    Be supportive and educational."""),
    ("user", """Provide feedback for:
    Question: {question}
    Correct Answer: {correct_answer}
    User's Answer: {user_answer}
    Math Topic: {math_topic}""")
])

# Define the node functions
def create_story(state: State) -> State:
    chain = story_prompt | llm | StrOutputParser()
    story = chain.invoke({
        "math_topic": state["math_topic"],
        "story_context": state["story_context"],
        "character": state["character"]
    })
    return {**state, "story": story}

def generate_questions(state: State) -> State:
    chain = questions_prompt | llm | StrOutputParser()
    questions_text = chain.invoke({
        "story": state["story"],
        "math_topic": state["math_topic"]
    })
    
    # Parse questions into a list of dictionaries
    questions = []
    current_question = None
    current_answer = None
    
    for line in questions_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('Question'):
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": current_answer
                })
            current_question = line.split(':', 1)[1].strip()
        elif line.startswith('Answer'):
            current_answer = line.split(':', 1)[1].strip()
    
    # Add the last question if exists
    if current_question and current_answer:
        questions.append({
            "question": current_question,
            "answer": current_answer
        })
    
    # Ensure we have at least one question
    if not questions:
        questions = [{
            "question": "What is the main mathematical concept in the story?",
            "answer": "The main mathematical concept is " + state["math_topic"]
        }]
    
    return {**state, "questions": questions}

def get_user_answer(state: State) -> State:
    if not state["questions"]:
        print("Error: No questions generated. Using default question.")
        state["questions"] = [{
            "question": "What is the main mathematical concept in the story?",
            "answer": "The main mathematical concept is " + state["math_topic"]
        }]
    
    print("\nStory:", state["story"])
    print("\nQuestion:", state["questions"][0]["question"])
    user_answer = input("Your answer: ")
    return {**state, "user_answer": user_answer}

def provide_feedback(state: State) -> State:
    chain = feedback_prompt | llm | StrOutputParser()
    feedback = chain.invoke({
        "question": state["questions"][0]["question"],
        "correct_answer": state["questions"][0]["answer"],
        "user_answer": state["user_answer"],
        "math_topic": state["math_topic"]
    })
    return {**state, "feedback": feedback}

# Create the graph
graph = StateGraph(State)

# Add nodes
graph.add_node("create_story", create_story)
graph.add_node("generate_questions", generate_questions)
graph.add_node("get_user_answer", get_user_answer)
graph.add_node("provide_feedback", provide_feedback)

# Define the workflow
graph.set_entry_point("create_story")
graph.add_edge("create_story", "generate_questions")
graph.add_edge("generate_questions", "get_user_answer")
graph.add_edge("get_user_answer", "provide_feedback")
graph.add_edge("provide_feedback", END)

# Compile the graph
app = graph.compile()

# Get user inputs
print("Welcome to the Interactive Math Story Generator!")
math_topic = input("Enter a math topic (e.g., 'fractions', 'algebra', 'geometry'): ")
story_context = input("Enter a story context (e.g., 'Harry Potter', 'Star Wars'): ")
character = input("Enter a character from the context: ")

# Execute the workflow
inputs = {
    "math_topic": math_topic,
    "story_context": story_context,
    "character": character
}

result = app.invoke(inputs)

# Print the final feedback
print("\nFeedback:", result["feedback"])
