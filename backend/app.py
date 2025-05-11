from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate # Updated import from langchain.prompts
from langchain.schema import StrOutputParser # Langchain core StrOutputParser
import json
import re
from typing import Dict, Any, Union

# Load environment variables
load_dotenv('api.env')

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
MAX_STEPS = 5

# LangChain Gemini model
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    logger.error("GEMINI_API_KEY not found in environment variables.")
    # Consider exiting or raising an error if the API key is critical for startup
    # exit(1)

try:
    llm = ChatGoogleGenerativeAI(
        # The model name "models/gemini-2.0-flash" is kept as per your code.
        # For "gemini-1.5-flash", the identifier is typically "gemini-1.5-flash-latest" or "gemini-1.5-flash".
        # Please ensure "models/gemini-2.0-flash" is the correct and available identifier for your setup.
        model="models/gemini-2.0-flash",
        temperature=0.8,
        google_api_key=api_key,
        max_output_tokens=2048,
        top_p=0.8,
        top_k=40,
        convert_system_message_to_human=True
    )
    logger.info("ChatGoogleGenerativeAI model initialized.")
except Exception as e:
    logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}")
    llm = None # Handle cases where LLM might not initialize

# --- Prompt Templates ---
story_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a fast-paced storyteller and math educator for ages 10-12. Every scene must center on the chosen math topic and drive the plot forward with action.
    Keep each chapter very concise and eventful, integrating the math topic naturally. Do not lose focus on the math_topic.
    Ensure the story is coherent with the user's choices and previous chapters.
    """),
    ("human", """
    Create a story scene for a student (age 10-12) that stays focused on the math topic: {math_topic}.
    The character is: {character}.
    This is Scene {step}.

    Previous scene context or initial setting (note: the current scene should coherent but different):
    {story_context}

    User's choice from the previous scene (if any): {user_choice}

    User's favorite activities: {favorite_activities}

    Instructions for this scene:
    - The scene should be no more than 2 sentences, packed with action or plot twists.
    - Try and add information about the favorite activities to the scene.
    - Introduce a situation that requires mathematical thinking around {math_topic}, without spelling out the problem.
    - Offer 3 possible approaches or solutions related to the situation; only one is correct.
    - Return only a JSON object with the following fields: "sceneText", "questions" (with "prompt", "choices", "answer", "feedback"), "metaphor", "mathConcept". Example:
    {{
      "sceneText": "The ground shakes and a chasm opens! To cross, you must quickly estimate the number of logs needed...",
      "questions": [
        {{
          "prompt": "How many logs might you need if each log is 1 unit wide and the chasm appears to be 7 units across?",
          "choices": ["About 3 logs", "About 7 logs", "About 12 logs"],
          "answer": "About 7 logs",
          "feedback": ["Think if that's enough!", "Good estimation!", "That might be too many!"]
        }}
      ],
      "metaphor": "Bridging the gap with numbers.",
      "mathConcept": "Estimation"
    }}
    Do NOT include "progress", "score", or "finished" fields in your JSON response.
    """)
])

advice_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a supportive math tutor offering concise, actionable feedback.
    Focus on one key insight per missed question and link it directly to the math_topic.
    Keep feedback short and encouraging.
    """),
    ("human", """
    The student missed these questions on {math_topic}:
    {missed_questions_details}
    Provide a brief, positive summary with one clear tip per missed question.
    """)
])

theory_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an engaging math educator explaining ideas in simple terms for 10-12 year olds."),
    ("human", """
    Summarize the main concepts the student encountered about {math_topic} in up to 3 bullet points, based on these story metaphors:
    {story_metaphors}
    Keep it very short and fun.
    """)
])

principle_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a clear and concise math teacher for ages 10-12."),
    ("human", """
    For {math_topic}, state one memorable principle or law in one sentence, then add a one-sentence explanation.
    Return only that text.
    """)
])

def parse_llm_json_output(json_string: str) -> Union[Dict[str, Any], None]:
    """Safely parses JSON output from LLM, with regex fallback."""
    try:
        # Remove potential markdown ```json ... ```
        cleaned_output = re.sub(r"```json\s*(.*?)\s*```", r"\1", json_string, flags=re.DOTALL | re.IGNORECASE)
        return json.loads(cleaned_output)
    except json.JSONDecodeError:
        logger.warning(f"Initial JSON parsing failed for: {json_string[:200]}...") # Log snippet
        match = re.search(r'({[\s\S]*})', json_string)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e_regex:
                logger.error(f"Regex fallback JSON parsing failed: {e_regex} for output snippet: {match.group(1)[:200]}...")
                return None
        else:
            logger.error(f"Failed to extract JSON with regex from: {json_string[:200]}...")
            return None

@app.route('/api/intro', methods=['GET'])
def get_intro():
    return jsonify({
        "questions": [
            "What are your favorite things to do? (e.g., sports, games, books, movies)",
            "What kind of story do you want? (e.g., fantasy, sci-fi, adventure)",
            "Who is the main character? (e.g., wizard, explorer, detective)",
            "Which math topic should the story focus on?"
        ]
    })

@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    if not llm:
        return jsonify({'error': 'LLM not available'}), 503
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        initial_story_context = data.get('storyContext', 'a mysterious ancient ruin')
        character_name = data.get('character', 'a brave explorer')
        math_topic_choice = data.get('mathTopic', 'fractions')
        
        step = 1
        current_score = 0
        
        chain = story_prompt | llm | StrOutputParser()
        llm_response_json_str = chain.invoke({
            "math_topic": math_topic_choice,
            "story_context": initial_story_context, # For step 1, this is the initial setting
            "character": character_name,
            "step": step,
            # "score": current_score, # LLM doesn't need score as input for generation
            "user_choice": "Let's begin!", # Placeholder for the first scene
            "favorite_activities": data.get('favoriteActivities', 'unknown')
        })
        
        scene_data = parse_llm_json_output(llm_response_json_str)
        if not scene_data:
            logger.error(f"Failed to parse story JSON from LLM for generate-story: {llm_response_json_str}")
            return jsonify({'error': 'Failed to parse story from LLM.', 'llm_raw_response': llm_response_json_str}), 500

        # Ensure core fields from LLM are present, if not, use defaults or handle error
        scene_data.setdefault('sceneText', 'Error: Story scene not generated.')
        scene_data.setdefault('questions', [])
        scene_data.setdefault('metaphor', '')
        scene_data.setdefault('mathConcept', math_topic_choice) # Default to chosen topic

        # Backend-managed fields
        scene_data['progress'] = round(step / MAX_STEPS, 2)
        scene_data['step'] = step
        scene_data['score'] = current_score
        scene_data['answers'] = [] # Initialize list for user's answers
        scene_data['finished'] = False
        scene_data['metaphors'] = [scene_data.get('metaphor', '')] # Store metaphors over time
        scene_data['mathConcepts'] = [scene_data.get('mathConcept', math_topic_choice)]
        
        # Store initial settings in the scene for consistency in progress-story
        scene_data['mathTopic'] = math_topic_choice
        scene_data['character'] = character_name
        scene_data['initialStoryContext'] = initial_story_context # Store for potential reference if needed

        if 'imageRef' in scene_data: del scene_data['imageRef'] # As per original code

        return jsonify(scene_data)

    except Exception as e:
        logger.error(f"Error in /api/generate-story: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred.'}), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    if not llm:
        return jsonify({'error': 'LLM not available'}), 503
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        current_scene_data = data.get('currentScene')
        if not current_scene_data:
            return jsonify({'error': 'currentScene data is missing from request'}), 400
        
        user_choice_for_prompt = data.get('choice') # User's answer to the previous question

        # --- Retrieve consistent story parameters from current_scene_data ---
        math_topic = current_scene_data.get('mathTopic')
        if not math_topic:
            logger.error("Math topic missing from currentScene in /progress-story.")
            return jsonify({'error': 'Critical state missing: mathTopic.'}), 400
        
        character = current_scene_data.get('character', 'the protagonist') # Default if somehow missing
        
        # Context for the LLM is the text of the previous scene
        previous_scene_text = current_scene_data.get('sceneText', 'The adventure continued...')
        if not previous_scene_text: # Should not happen if generate_story is correct
             logger.warning("sceneText missing from currentScene, using generic context.")


        # --- Update state based on user's last choice ---
        step = current_scene_data.get('step', 0) + 1 # Increment step
        score = current_scene_data.get('score', 0)
        recorded_answers = list(current_scene_data.get('answers', [])) # Ensure it's a list
        collected_metaphors = list(current_scene_data.get('metaphors', []))
        collected_math_concepts = list(current_scene_data.get('mathConcepts', []))

        if user_choice_for_prompt is not None and current_scene_data.get('questions'):
            last_question_data = current_scene_data['questions'][0]
            correct_answer = last_question_data.get('answer')
            question_prompt_text = last_question_data.get('prompt')
            
            recorded_answers.append({
                'question': question_prompt_text,
                'your_answer': user_choice_for_prompt,
                'correct_answer': correct_answer
            })
            if user_choice_for_prompt == correct_answer:
                score += 1
        
        # --- Check if story is finished ---
        if step > MAX_STEPS:
            final_advice = "Great job! You answered all correctly!"
            final_theory = ""
            final_principle = ""

            wrong_answers = [ans for ans in recorded_answers if ans['your_answer'] != ans['correct_answer']]
            if wrong_answers:
                missed_details = "\n".join([
                    f"Question: {ans['question']}\nYour Answer: {ans['your_answer']}\nCorrect: {ans['correct_answer']}" 
                    for ans in wrong_answers
                ])
                try:
                    final_advice = (advice_prompt | llm | StrOutputParser()).invoke({
                        'missed_questions_details': missed_details,
                        'math_topic': math_topic
                        })
                except Exception as e_advice:
                    logger.error(f"Error generating advice: {e_advice}")
                    final_advice = "Could not generate personalized advice at this time. Keep practicing!"
            
            try:
                final_theory = (theory_prompt | llm | StrOutputParser()).invoke({
                    'math_topic': math_topic,
                    'story_metaphors': '\n'.join(filter(None, collected_metaphors))
                })
            except Exception as e_theory:
                logger.error(f"Error generating theory summary: {e_theory}")
                final_theory = "Could not generate theory summary."

            try:
                final_principle = (principle_prompt | llm | StrOutputParser()).invoke({
                    'math_topic': math_topic
                })
            except Exception as e_principle:
                logger.error(f"Error generating principle: {e_principle}")
                final_principle = "Could not generate math principle explanation."

            return jsonify({
                'sceneText': final_advice, # Main text for the final screen
                'progress': 1.0,
                'questions': [],
                'finished': True,
                'score': score,
                'step': step,
                'answers': recorded_answers,
                'metaphors': collected_metaphors,
                'mathConcepts': collected_math_concepts,
                'theorySummary': final_theory,
                'principleSummary': final_principle,
                'mathTopic': math_topic # Include for consistency
            })

        # --- Generate next story scene ---
        chain = story_prompt | llm | StrOutputParser()
        llm_response_json_str = chain.invoke({
            "math_topic": math_topic,
            "story_context": previous_scene_text, # Pass the narrative of the last scene
            "character": character,
            "step": step,
            # "score": score, # LLM does not set the score
            "user_choice": user_choice_for_prompt if user_choice_for_prompt is not None else "I'm ready for more!",
            "favorite_activities": data.get('favoriteActivities', 'unknown')
        })

        next_scene_data = parse_llm_json_output(llm_response_json_str)
        if not next_scene_data:
            logger.error(f"Failed to parse story JSON from LLM for progress-story: {llm_response_json_str}")
            # Fallback or error response
            # You could return the current state with an error message, or try to end the story gracefully
            return jsonify({
                'error': 'Failed to generate next part of the story.', 
                'llm_raw_response': llm_response_json_str,
                **current_scene_data, # Return previous valid state with error
                'sceneText': current_scene_data.get('sceneText', '') + "\n\n(Oops, the storyteller got lost! Try again or this might be the end of this path.)"
            }), 500
        
        next_scene_data.setdefault('sceneText', 'Error: Next scene not generated.')
        next_scene_data.setdefault('questions', [])
        
        # Update lists
        new_metaphor = next_scene_data.get('metaphor', '')
        if new_metaphor: collected_metaphors.append(new_metaphor)
        
        new_math_concept = next_scene_data.get('mathConcept', math_topic) # Default to main topic
        if new_math_concept: collected_math_concepts.append(new_math_concept)

        # Backend-managed fields for the new scene
        next_scene_data['progress'] = round(min(1.0, step / MAX_STEPS), 2)
        next_scene_data['step'] = step
        next_scene_data['score'] = score
        next_scene_data['answers'] = recorded_answers
        next_scene_data['finished'] = False
        next_scene_data['metaphors'] = collected_metaphors
        next_scene_data['mathConcepts'] = collected_math_concepts
        
        # Carry over consistent story parameters
        next_scene_data['mathTopic'] = math_topic
        next_scene_data['character'] = character
        next_scene_data['initialStoryContext'] = current_scene_data.get('initialStoryContext', '')


        if 'imageRef' in next_scene_data: del next_scene_data['imageRef']

        return jsonify(next_scene_data)

    except Exception as e:
        logger.error(f"Error in /api/progress-story: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred.'}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)