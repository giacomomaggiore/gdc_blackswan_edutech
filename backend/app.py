from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import json

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
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")
    raise

# Store user sessions and their story progress
user_sessions = {}

# This would typically come from a database, but for now we'll hardcode it
TEACHER_SETTINGS = {
    "math_topic": "inequalities",  # This would be set by the teacher
    "age_group": "8-12"
}

# Add a scoring and progress system
MAX_STEPS = 5  # For demo, end after 5 steps

def is_answer_correct(ai_options, user_choice):
    # For demo, randomly pick the first option as correct
    return user_choice == ai_options[0]

def generate_story_prompt(interests):
    return f"""Create a short, engaging, and age-appropriate STEM story for children aged {TEACHER_SETTINGS['age_group']} that incorporates the following:
    - The student's interests: {interests}
    - The mathematical topic to teach: {TEACHER_SETTINGS['math_topic']}
    - Do NOT mention or reference quantum physics or advanced science topics.
    
    The story should:
    1. Be only 2-3 sentences long for each segment, keeping it concise and easy to read.
    2. Use simple, clear language appropriate for {TEACHER_SETTINGS['age_group']} year olds.
    3. Be fun and relatable, and avoid advanced or confusing topics.
    4. End with a multiple-choice question (2-3 options) that relates to the story and the math topic. The question should be clear and age-appropriate.
    5. Do NOT reference quantum physics or advanced science.
    6. Do NOT continue the story until the user chooses an answer.
    
    Format the response as JSON with the following structure:
    {{
        "sceneText": "The story text for this segment (2-3 sentences)",
        "imageRef": "A description of what the scene should look like",
        "question": "A multiple-choice question for the user",
        "options": ["Option 1", "Option 2", "Option 3"]
    }}
    """

@app.route('/api/intro', methods=['GET'])
def get_intro():
    return jsonify({
        "questions": [
            "What are your favorite things to do? (e.g., sports, games, books, movies, etc.)"
        ]
    })

@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    try:
        data = request.json
        interests = data.get('interests', '')
        
        # Generate story using Gemini
        response = model.generate_content(generate_story_prompt(interests))
        
        # Parse the response and return the story
        try:
            raw_text = response.text.strip()
            if raw_text.startswith('```json'):
                raw_text = raw_text[len('```json'):].strip()
            if raw_text.startswith('```'):
                raw_text = raw_text[len('```'):].strip()
            if raw_text.endswith('```'):
                raw_text = raw_text[:-len('```')].strip()
            story_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON. Raw response: {response.text}")
            logger.error(f"JSONDecodeError: {str(e)}")
            return jsonify({
                "error": "Failed to generate a valid story. Please try again.",
                "details": "The AI response was not in the expected format."
            }), 500
        
        session_id = str(len(user_sessions) + 1)
        user_sessions[session_id] = {
            'current_scene': story_data,
            'interests': interests,
            'score': 0,
            'step': 1
        }
        story_data['sessionId'] = session_id
        story_data['progress'] = 1 / MAX_STEPS
        story_data['score'] = 0
        story_data['finished'] = False
        return jsonify(story_data)
    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}")
        return jsonify({
            "error": "Failed to generate story",
            "details": str(e)
        }), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    data = request.json
    session_id = data.get('sessionId')
    choice = data.get('choice')
    
    if session_id not in user_sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = user_sessions[session_id]
    current_scene = session['current_scene']
    step = session['step']
    score = session['score']
    
    # Check if answer is correct
    correct = is_answer_correct(current_scene['options'], choice)
    feedback = "Correct! Well done!" if correct else "Not quite right. Try again!"
    if correct:
        score += 1
    step += 1
    
    finished = step > MAX_STEPS
    if finished:
        return jsonify({
            "sceneText": f"The adventure is over! Your final score: {score}/{MAX_STEPS}.",
            "imageRef": "A celebratory scene with confetti.",
            "question": None,
            "options": [],
            "sessionId": session_id,
            "progress": 1.0,
            "score": score,
            "finished": True,
            "feedback": feedback
        })
    
    # Generate next scene
    next_scene_prompt = f"""Based on the previous scene:
    {current_scene}
    
    And the user's choice:
    {choice}
    
    Continue the story with another short segment (2-3 sentences), keeping it simple and fun for {TEACHER_SETTINGS['age_group']} year olds. Do NOT reference quantum physics or advanced science. End with a new multiple-choice question (2-3 options) related to the story and the math topic. Do NOT continue the story until the user chooses an answer.
    
    Format as JSON with:
    {{
        "sceneText": "The story text for this segment (2-3 sentences)",
        "imageRef": "A description of what the scene should look like",
        "question": "A multiple-choice question for the user",
        "options": ["Option 1", "Option 2", "Option 3"]
    }}
    """
    response = model.generate_content(next_scene_prompt)
    try:
        raw_text = response.text.strip()
        if raw_text.startswith('```json'):
            raw_text = raw_text[len('```json'):].strip()
        if raw_text.startswith('```'):
            raw_text = raw_text[len('```'):].strip()
        if raw_text.endswith('```'):
            raw_text = raw_text[:-len('```')].strip()
        next_scene = json.loads(raw_text)
        session['current_scene'] = next_scene
        session['score'] = score
        session['step'] = step
        next_scene['sessionId'] = session_id
        next_scene['progress'] = step / MAX_STEPS
        next_scene['score'] = score
        next_scene['finished'] = False
        next_scene['feedback'] = feedback
        return jsonify(next_scene)
    except Exception as e:
        logger.error(f"Failed to parse Gemini response as JSON. Raw response: {response.text}")
        logger.error(f"Exception: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 