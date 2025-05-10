from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from api.env
load_dotenv('api.env')

app = Flask(__name__)
CORS(app)

# Configure Gemini API
try:
    api_key = os.getenv('GEMINI_API_KEY')
    logger.debug(f"API Key loaded: {'Yes' if api_key else 'No'}")
    genai.configure(api_key=api_key)
    
    # Initialize the Gemini model with system message conversion
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-2.0-flash",
        temperature=0.7,
        google_api_key=api_key,
        max_output_tokens=2048,
        top_p=0.8,
        top_k=40,
        convert_system_message_to_human=True  # Convert system messages to human messages
    )
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")
    raise

# Store user sessions and their story progress
user_sessions = {}

# Create prompt templates for different stages
story_prompt = ChatPromptTemplate.from_messages([
    ("human", """You are a creative storyteller. Create a short, engaging STEM story that:
    1. Takes place in the given context
    2. Features the chosen character
    3. Naturally incorporates the mathematical concept
    4. Creates a branching narrative that can change based on character decisions
    5. Ends with a multiple-choice question that tests the mathematical concept
    
    Important rules:
    - The story must be concise (maximum 200-300 words)
    - Each paragraph should be short and direct
    - Use simple, clear language
    - Keep the story engaging and educational
    - Make the reader feel like they are the character
    - End with a clear multiple-choice question with 2-3 options
    - Format the question as "Do you: A) [option 1]? B) [option 2]? C) [option 3]?"
    - After each option, include the consequence in parentheses: "(If [option] is chosen): [consequence]"
    
    Create a short story with these elements:
    Mathematical Topic: {math_topic}
    Story Context: {story_context}
    Character: {character}""")
])

questions_prompt = ChatPromptTemplate.from_messages([
    ("human", """You are a creative educator. Create 3 interactive questions that:
    1. Are directly connected to the story
    2. Verify understanding of the mathematical concept
    3. Are engaging and contextual
    4. Make the reader think as if they were the character
    5. Have clear consequences for the answer
    
    Format each question exactly like this:
    Question 1: [question text that makes the reader think as the character]
    Answer 1: [answer text]
    Consequences:
    - Correct: [what happens if the answer is correct]
    - Wrong: [what happens if the answer is wrong]
    
    Question 2: [question text that makes the reader think as the character]
    Answer 2: [answer text]
    Consequences:
    - Correct: [what happens if the answer is correct]
    - Wrong: [what happens if the answer is wrong]
    
    Question 3: [question text that makes the reader think as the character]
    Answer 3: [answer text]
    Consequences:
    - Correct: [what happens if the answer is correct]
    - Wrong: [what happens if the answer is wrong]
    
    Create questions based on:
    Story: {story}
    Mathematical Topic: {math_topic}
    Character: {character}""")
])

continuation_prompt = ChatPromptTemplate.from_messages([
    ("human", """You are a creative storyteller. Continue the story based on the character's answer:
    1. If the answer is correct, continue with the best possible outcome
    2. If the answer is wrong, create a challenging situation the character must overcome
    Keep the story engaging and maintain the character's personality.
    
    Continue the story based on:
    Previous Story: {story}
    Question: {question}
    Character's Answer: {user_answer}
    Correct Answer: {correct_answer}
    Is Correct: {is_correct}
    Character: {character}
    Mathematical Topic: {math_topic}""")
])

feedback_prompt = ChatPromptTemplate.from_messages([
    ("human", """You are a math tutor and roleplay guide. Provide feedback that:
    1. Evaluates the correctness of the answer
    2. Explains the mathematical concept if needed
    3. Encourages further learning
    4. Maintains the character's perspective
    5. Suggests how the character could have approached the problem
    Be encouraging and educational while keeping the roleplay engaging.
    
    Provide feedback for:
    Question: {question}
    Correct Answer: {correct_answer}
    User's Answer: {user_answer}
    Mathematical Topic: {math_topic}
    Character: {character}""")
])

def parse_story_and_question(story_text):
    """Parse the story text to extract the story, question, and options."""
    # Split the story into parts
    parts = story_text.split("Do you:")
    if len(parts) != 2:
        return {
            "story": story_text,
            "question": "What would you do next?",
            "options": ["Continue", "Turn back"]
        }
    
    story = parts[0].strip()
    question_part = parts[1].strip()
    
    # Extract options and their consequences
    options = []
    current_option = None
    current_consequence = None
    
    for line in question_part.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('A)') or line.startswith('B)') or line.startswith('C)'):
            if current_option and current_consequence:
                options.append({
                    "text": current_option,
                    "consequence": current_consequence
                })
            option_parts = line.split('?', 1)
            current_option = option_parts[0].strip()
            if len(option_parts) > 1:
                current_consequence = option_parts[1].strip()
        elif line.startswith('(If'):
            if current_consequence:
                current_consequence += " " + line.strip('()')
    
    if current_option and current_consequence:
        options.append({
            "text": current_option,
            "consequence": current_consequence
        })
    
    return {
        "story": story,
        "question": f"Do you: {', '.join(opt['text'] for opt in options)}?",
        "options": [opt['text'] for opt in options],
        "consequences": {opt['text']: opt['consequence'] for opt in options}
    }

@app.route('/api/intro', methods=['GET'])
def get_intro():
    return jsonify({
        "questions": [
            "What are your favorite things to do? (e.g., sports, games, books, movies, etc.)",
            "What kind of story would you like to be part of? (e.g., fantasy, sci-fi, adventure)",
            "Who would you like to be in this story? (e.g., a wizard, a space explorer, a detective)"
        ]
    })

@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    try:
        data = request.json
        interests = data.get('interests', '')
        story_context = data.get('storyContext', 'fantasy world')
        character = data.get('character', 'adventurer')
        math_topic = data.get('mathTopic', 'basic arithmetic')
        
        # Generate initial story
        story_chain = story_prompt | llm | StrOutputParser()
        story_text = story_chain.invoke({
            "math_topic": math_topic,
            "story_context": story_context,
            "character": character
        })
        
        # Parse the story and extract question/options
        parsed_story = parse_story_and_question(story_text)
        
        session_id = str(len(user_sessions) + 1)
        user_sessions[session_id] = {
            'story': parsed_story['story'],
            'current_question': parsed_story['question'],
            'options': parsed_story['options'],
            'consequences': parsed_story['consequences'],
            'character': character,
            'math_topic': math_topic,
            'score': 0,
            'step': 1
        }
        
        # Format response to match expected structure
        return jsonify({
            "sessionId": session_id,
            "sceneText": parsed_story['story'],
            "imageRef": f"A scene featuring {character} in {story_context}",
            "question": parsed_story['question'],
            "options": parsed_story['options'],
            "progress": 0.25,  # First step of 4
            "score": 0,
            "finished": False
        })
    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}")
        return jsonify({
            "error": "Failed to generate story",
            "details": str(e)
        }), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    try:
        data = request.json
        session_id = data.get('sessionId')
        user_answer = data.get('choice')
        
        if session_id not in user_sessions:
            return jsonify({"error": "Invalid session"}), 400
        
        session = user_sessions[session_id]
        
        # Get the consequence for the chosen option
        consequence = session['consequences'].get(user_answer, "You continue your journey.")
        
        # Generate story continuation
        continuation_chain = continuation_prompt | llm | StrOutputParser()
        continuation = continuation_chain.invoke({
            "story": session['story'],
            "question": session['current_question'],
            "user_answer": user_answer,
            "correct_answer": session['options'][0],  # For now, assume first option is correct
            "is_correct": user_answer == session['options'][0],
            "character": session['character'],
            "math_topic": session['math_topic']
        })
        
        # Update session
        session['story'] += "\n\n" + consequence + "\n\n" + continuation
        session['step'] += 1
        
        # Check if story is finished (after 4 steps)
        finished = session['step'] > 4
        
        if finished:
            return jsonify({
                "sceneText": session['story'],
                "imageRef": "A celebratory scene with confetti",
                "question": None,
                "options": [],
                "progress": 1.0,
                "score": session['score'],
                "finished": True
            })
        
        # Generate next part of the story
        story_chain = story_prompt | llm | StrOutputParser()
        next_story_text = story_chain.invoke({
            "math_topic": session['math_topic'],
            "story_context": "continuing the adventure",
            "character": session['character']
        })
        
        # Parse the next part
        parsed_story = parse_story_and_question(next_story_text)
        
        # Update session with new question and options
        session['current_question'] = parsed_story['question']
        session['options'] = parsed_story['options']
        session['consequences'] = parsed_story['consequences']
        
        return jsonify({
            "sceneText": session['story'],
            "imageRef": f"A scene featuring {session['character']} facing a new challenge",
            "question": parsed_story['question'],
            "options": parsed_story['options'],
            "progress": session['step'] / 4,
            "score": session['score'],
            "finished": False
        })
    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}")
        return jsonify({
            "error": "Failed to progress story",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 