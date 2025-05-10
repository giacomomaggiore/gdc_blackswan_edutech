from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import json
import re
from typing import List, Optional, Union, Dict, Any

# Pydantic V2 imports
from pydantic import BaseModel, Field, ValidationError

# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# === load env & configure Flask ===
load_dotenv('api.env')
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === LLM setup ===
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    logger.error("GEMINI_API_KEY not found in environment variables.")
    # exit(1) # Or handle this more gracefully depending on your deployment

# Updated LLM initialization
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", # Updated model name, check for latest
        temperature=0.9,
        google_api_key=api_key,
        max_output_tokens=2048,
        top_p=0.8,
        top_k=40,
        convert_system_message_to_human=True # This might be default or handled differently now
    )
    logger.info("Google Gemini LLM initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None # Ensure llm is None if initialization fails

# --- Pydantic Models ---

class SceneQuestion(BaseModel):
    prompt: str
    choices: List[str]
    answer: str
    feedback: List[str]

class BaseScene(BaseModel):
    scene_text: str = Field(..., alias='sceneText')
    image_ref: Optional[str] = Field(None, alias='imageRef') # Make optional if not always present
    progress: float
    questions: List[SceneQuestion]
    metaphor: Optional[str] = None # Make optional as per example
    math_concept: Optional[str] = Field(None, alias='mathConcept') # Make optional
    finished: bool
    score: int
    step: int
    answers: List[Dict[str, str]] = Field(default_factory=list)
    metaphors: List[str] = Field(default_factory=list)
    math_concepts: List[str] = Field(default_factory=list, alias='mathConcepts')
    story_history: List[str] = Field(default_factory=list, alias='storyHistory')

class StoryResponse(BaseScene):
    pass

class FinishedStoryResponse(BaseModel):
    scene_text: str = Field(..., alias='sceneText') # advice message
    image_ref: Optional[str] = Field(None, alias='imageRef')
    progress: float
    questions: List[SceneQuestion] = Field(default_factory=list) # Empty for finished
    finished: bool
    score: int
    answers: List[Dict[str, str]]
    step: int
    theory_summary: str = Field(..., alias='theorySummary')
    principle_summary: str = Field(..., alias='principleSummary')
    metaphors: List[str]
    math_concepts: List[str] = Field(..., alias='mathConcepts')
    story_history: List[str] = Field(..., alias='storyHistory')


class GenerateStoryRequest(BaseModel):
    story_context: str = Field("fantasy world", alias='storyContext')
    character: str = "adventurer"
    math_topic: Optional[str] = Field("algebra", alias='mathTopic')

class ProgressStoryRequest(BaseModel):
    story_context: str = Field("fantasy world", alias='storyContext')
    character: str = "adventurer"
    math_topic: str = Field(..., alias='mathTopic')
    current_scene: BaseScene = Field(..., alias='currentScene')
    choice: Optional[str] = None


# --- Prompt templates (unchanged from original, but ensure they are robust) ---
story_prompt = PromptTemplate(
    input_variables=["math_topic", "story_context", "character", "step", "story_history"], # Added story_history
    template=(
        "You are a masterful storyteller and math educator who specializes in creating engaging, educational stories for young students.\n"
        "Your stories should:\n"
        "- Be immersive and captivating, drawing students into the narrative\n"
        "- Naturally integrate mathematical concepts without explicitly stating them\n"
        "- Encourage students to discover and formulate problems themselves\n"
        "- Use clear, simple, age-appropriate language for 10-12 year olds\n"
        "- Keep the story concise and easy to follow\n"
        "- Create meaningful connections between story elements and mathematical thinking\n"
        "- Maintain a consistent tone and style throughout the narrative\n"
        "- Include subtle metaphors that help students understand abstract concepts\n"
        "- Balance entertainment with educational value\n"
        "Create a short, simple STEM story scene for a student (age 10-12).\n"
        "- For the first scene (step 1), write a brief introduction (3-4 sentences) that sets up the world, characters, and initial situation. Make it easy to understand.\n"
        "- For subsequent scenes (step > 1), use the provided 'Previous scenes' to write the next part of the story. Keep new scenes very concise (2-3 sentences) and focus on the evolving narrative, referencing previous events to maintain continuity.\n"
        "- The story should feel continuous and connected, referencing previous events and maintaining narrative continuity.\n"
        "- Instead of explicitly stating a math problem, present a situation that requires mathematical thinking. Let the student identify and formulate the problem themselves.\n"
        "- At the end of each scene, present a situation that requires mathematical thinking, but don't explicitly state it as a math problem.\n"
        "- Provide 3 possible approaches or solutions, only one of which is correct.\n"
        "- For each choice, provide a brief feedback string that guides the student's thinking.\n"
        "- Include a subtle metaphor that relates the story situation to the math concept, but don't explicitly state the connection.\n"
        "- Return ONLY a JSON object in this format:\n"
        "{{\n"
        "  'sceneText': '...',\n"
        "  'imageRef': '... (e.g., a brief description for an image generation model like 'mystical_cave_entrance.png' or 'character_solving_puzzle_with_glowing_runes')',\n"
        "  'progress': 0.2,  // This is a placeholder, the backend will calculate actual progress \n"
        "  'questions': [\n"
        "    {{\n"
        "      'prompt': '... (The situation that requires mathematical thinking)',\n"
        "      'choices': ['...', '...', '...'],\n"
        "      'answer': '... (The correct choice text)',\n"
        "      'feedback': ['... (Feedback for choice 1)', '... (Feedback for choice 2)', '... (Feedback for choice 3)']\n"
        "    }}\n"
        "  ],\n"
        "  'metaphor': '... (The subtle metaphor for this scene)',\n"
        "  'mathConcept': '... (The specific math concept hinted at in this scene, e.g., 'basic addition', 'pattern recognition')',\n"
        "  'finished': false, // This is a placeholder, the backend will manage this \n"
        "  'score': 0       // This is a placeholder, the backend will manage this \n"
        "}}\n"
        "The math topic is: {math_topic}\n"
        "The story context is: {story_context}\n"
        "The main character is: {character}\n"
        "The current step is: {step}\n"
        "Previous scenes (for context, only if step > 1):\n{story_history}\n"
        "Respond with ONLY the JSON object, no explanation or extra text."
    )
)

advice_prompt = PromptTemplate(
    input_variables=["missed"],
    template=(
        "You are a supportive and encouraging math tutor who specializes in helping students understand mathematical concepts through their own discoveries.\n"
        "Your feedback should:\n"
        "- Focus on the student's problem-solving approach rather than just the final answer\n"
        "- Highlight the positive aspects of their thinking\n"
        "- Guide them toward deeper understanding\n"
        "- Connect their attempts to the underlying mathematical concepts\n"
        "- Maintain an encouraging and positive tone\n"
        "- Provide concrete, actionable advice for improvement\n"
        "Given a list of missed questions, the student's answers, and the correct answers, write a short, encouraging summary for the student. For each missed question, provide a concrete explanation of the math concept and advice on how to improve. End with a positive message.\n"
        "Focus on the student's problem-solving approach rather than just the final answer.\n"
        "Missed questions:\n{missed}"
    )
)

theory_prompt = PromptTemplate(
    input_variables=["math_topic", "metaphors", "story_history", "answers"],
    template=(
        "You are an engaging math educator who explains key ideas in a few words for 10-12 year olds.\n"
        "Your summaries should:\n"
        "- Be very short and clear\n"
        "- Use simple, age-appropriate language\n"
        "- List only the most important concepts\n"
        "Write a very short summary of the main math ideas from this story for a 10-12 year old.\n"
        "- List the key concepts they learned based on the story scenes and answers.\n"
        "- Keep it simple and fun.\n"
        "Math topic: {math_topic}\n"
        "Story metaphors used: {metaphors}\n"
        "Story scenes experienced: {story_history}\n"
        "User answers during the story: {answers}"
    )
)

principle_prompt = PromptTemplate(
    input_variables=["math_topic", "metaphors", "story_history", "answers"],
    template=(
        "You are a math teacher who explains core mathematical principles in a simple, clear way for 10-12 year olds.\n"
        "Your explanations should:\n"
        "- Be short, clear, and support markdown and LaTeX-style formulas (use $...$ for math)\n"
        "- Use a concrete example and a formula if applicable\n"
        "- Focus on the main principle behind the story's math topic\n"
        "- Make it memorable and practical\n"
        "- Add a brief theoretical explanation\n"
        "Write a short, clear explanation of the main mathematical principle used in this adventure. Use markdown and LaTeX-style formulas (e.g., $x+3=7$). Give a concrete example and a formula. Add a brief theoretical explanation. For example, if the story is about equations, explain why multiplying both sides by the same number keeps the equation valid.\n"
        "Math topic: {math_topic}\n"
        "Story metaphors used: {metaphors}\n"
        "Story scenes experienced: {story_history}\n"
        "User answers during the story: {answers}"
    )
)

def parse_llm_json_output(llm_output: str) -> Optional[Dict[str, Any]]:
    """Attempts to parse JSON from LLM output, with a regex fallback."""
    try:
        # Remove potential markdown ```json ... ```
        cleaned_output = re.sub(r"```json\s*(.*?)\s*```", r"\1", llm_output, flags=re.DOTALL)
        return json.loads(cleaned_output)
    except json.JSONDecodeError:
        logger.warning(f"Initial JSON parsing failed for: {llm_output}")
        match = re.search(r'({[\s\S]*})', llm_output)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"Regex fallback JSON parsing failed: {e} for output: {match.group(1)}")
                return None
        else:
            logger.error(f"Failed to extract JSON with regex from: {llm_output}")
            return None

@app.route('/api/generate-story', methods=['POST'])
def generate_story_route():
    if llm is None:
        return jsonify({'error': 'LLM not initialized. Please check API key and configuration.'}), 503

    try:
        request_data = GenerateStoryRequest.model_validate(request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request data', 'details': e.errors()}), 422
    except Exception: # Catch non-dict data
        return jsonify({'error': 'Invalid JSON data in request.'}), 400


    step = 1
    chain = story_prompt | llm | StrOutputParser()

    try:
        story_json_str = chain.invoke({
            "math_topic": request_data.math_topic or "algebra",
            "story_context": request_data.story_context,
            "character": request_data.character,
            "step": step,
            "story_history": "" # No history for the first step
        })
        logger.info(f"LLM Raw Output for new story: {story_json_str}")
        
        parsed_llm_dict = parse_llm_json_output(story_json_str)
        if not parsed_llm_dict:
            logger.error(f"Failed to parse story from LLM after regex: {story_json_str}")
            return jsonify({'error': 'Failed to parse story from LLM.', 'llm_raw_response': story_json_str}), 500

        # Validate LLM output against a partial Scene model or manually check keys
        # For simplicity, we'll assume the LLM follows the prompt reasonably well here.
        # In a production system, more robust validation of LLM output is recommended.

        scene_data = {
            'sceneText': parsed_llm_dict.get('sceneText', 'Error: Scene text missing.'),
            'imageRef': parsed_llm_dict.get('imageRef', ''),
            'questions': parsed_llm_dict.get('questions', []),
            'metaphor': parsed_llm_dict.get('metaphor'),
            'mathConcept': parsed_llm_dict.get('mathConcept'),
            'progress': 0.2, # Initial progress
            'score': 0,
            'step': step,
            'answers': [],
            'finished': False,
            'metaphors': [parsed_llm_dict.get('metaphor', '')] if parsed_llm_dict.get('metaphor') else [],
            'mathConcepts': [parsed_llm_dict.get('mathConcept', '')] if parsed_llm_dict.get('mathConcept') else [],
            'storyHistory': [parsed_llm_dict.get('sceneText', '')] if parsed_llm_dict.get('sceneText') else []
        }
        
        response_model = StoryResponse.model_validate(scene_data)
        return jsonify(response_model.model_dump(by_alias=True))

    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story_route():
    if llm is None:
        return jsonify({'error': 'LLM not initialized. Please check API key and configuration.'}), 503

    try:
        request_data = ProgressStoryRequest.model_validate(request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request data', 'details': e.errors()}), 422
    except Exception: # Catch non-dict data
        return jsonify({'error': 'Invalid JSON data in request.'}), 400

    prev_scene_model = request_data.current_scene
    step = prev_scene_model.step + 1
    score = prev_scene_model.score
    answers = list(prev_scene_model.answers) # Ensure it's a mutable list
    metaphors = list(prev_scene_model.metaphors)
    math_concepts = list(prev_scene_model.math_concepts)
    story_history = list(prev_scene_model.story_history) # Make a mutable copy

    user_choice = request_data.choice
    
    if prev_scene_model.questions: # Ensure there's a question to answer
        question_prompt_text = prev_scene_model.questions[0].prompt
        correct_answer = prev_scene_model.questions[0].answer
        if user_choice is not None:
            answers.append({
                'question': question_prompt_text,
                'your_answer': user_choice,
                'correct_answer': correct_answer
            })
            if user_choice == correct_answer:
                score += 1
    
    # Add current scene text to history before generating next or finishing
    if prev_scene_model.scene_text and prev_scene_model.scene_text not in story_history: # Avoid duplicates if logic allows
        story_history.append(prev_scene_model.scene_text)

    MAX_STEPS = 5 # Define max steps for the story
    if step > MAX_STEPS:
        advice = "You got all questions correct! Great job!"
        wrong_answers = [a for a in answers if a['your_answer'] != a['correct_answer']]
        if wrong_answers:
            missed_str = "\n".join([
                f"Q: {a['question']}\nYour answer: {a['your_answer']}\nCorrect answer: {a['correct_answer']}"
                for a in wrong_answers
            ])
            advice_chain = advice_prompt | llm | StrOutputParser()
            try:
                advice = advice_chain.invoke({"missed": missed_str})
            except Exception as e:
                logger.error(f"Error generating advice: {e}")
                advice = "There was an issue generating detailed advice, but keep practicing!"

        # Generate theoretical summary
        theory_chain = theory_prompt | llm | StrOutputParser()
        try:
            theory_summary = theory_chain.invoke({
                "math_topic": request_data.math_topic,
                "metaphors": "\n".join(filter(None, metaphors)),
                "story_history": "\n".join(filter(None,story_history)),
                "answers": json.dumps(answers)
            })
        except Exception as e:
            logger.error(f"Error generating theory summary: {e}")
            theory_summary = "Could not generate theory summary at this time."

        # Generate principle summary
        principle_chain = principle_prompt | llm | StrOutputParser()
        try:
            principle_summary = principle_chain.invoke({
                "math_topic": request_data.math_topic,
                "metaphors": "\n".join(filter(None, metaphors)),
                "story_history": "\n".join(filter(None,story_history)),
                "answers": json.dumps(answers)
            })
        except Exception as e:
            logger.error(f"Error generating principle summary: {e}")
            principle_summary = "Could not generate principle summary at this time."
        
        finished_response_data = {
            'sceneText': advice,
            'imageRef': '', # No image for advice screen usually
            'progress': 1.0,
            'questions': [],
            'finished': True,
            'score': score,
            'answers': answers,
            'step': step,
            'theorySummary': theory_summary,
            'principleSummary': principle_summary,
            'metaphors': metaphors,
            'mathConcepts': math_concepts,
            'storyHistory': story_history
        }
        response_model = FinishedStoryResponse.model_validate(finished_response_data)
        return jsonify(response_model.model_dump(by_alias=True))

    # Otherwise, generate next scene
    chain = story_prompt | llm | StrOutputParser()
    try:
        story_json_str = chain.invoke({
            "math_topic": request_data.math_topic,
            "story_context": request_data.story_context,
            "character": request_data.character,
            "step": step,
            "story_history": "\n---\n".join(filter(None,story_history)) # Pass previous scenes for context
        })
        logger.info(f"LLM Raw Output for step {step}: {story_json_str}")

        parsed_llm_dict = parse_llm_json_output(story_json_str)
        if not parsed_llm_dict:
            logger.error(f"Failed to parse story from LLM for step {step}: {story_json_str}")
            # Fallback: Create a simple error scene to allow continuation or end
            error_scene_data = {
                'sceneText': "Oops! The storyteller seems to have gotten lost. Let's try to get back on track or conclude here.",
                'imageRef': 'error_placeholder.png',
                'progress': min(1.0, (step -1) / MAX_STEPS), # Progress based on previous step
                'questions': [], # No new question if error
                'metaphor': 'A tangled thread',
                'mathConcept': 'Problem Solving',
                'finished': False, # Or True, if you want to end on error
                'score': score,
                'step': step,
                'answers': answers,
                'metaphors': metaphors,
                'mathConcepts': math_concepts,
                'storyHistory': story_history
            }
            if step > MAX_STEPS : # if error happens on the last step, finish
                 error_scene_data['finished'] = True
                 error_scene_data['progress'] = 1.0

            response_model = StoryResponse.model_validate(error_scene_data)
            return jsonify(response_model.model_dump(by_alias=True)), 200 # Return 200 so client can display this


        # Safely add new metaphor, mathConcept, sceneText to their respective lists
        new_metaphor = parsed_llm_dict.get('metaphor')
        if new_metaphor:
            metaphors.append(new_metaphor)
        
        new_math_concept = parsed_llm_dict.get('mathConcept')
        if new_math_concept:
            math_concepts.append(new_math_concept)
            
        new_scene_text = parsed_llm_dict.get('sceneText')
        # Story history already updated above with prev_scene_model.scene_text
        # The new_scene_text will be added to history in the *next* call to progress_story

        scene_data = {
            'sceneText': new_scene_text or "Error: Next scene text missing.",
            'imageRef': parsed_llm_dict.get('imageRef', ''),
            'questions': parsed_llm_dict.get('questions', []),
            'metaphor': new_metaphor,
            'mathConcept': new_math_concept,
            'progress': min(1.0, step / MAX_STEPS),
            'score': score,
            'step': step,
            'answers': answers, # list of dicts
            'finished': False,
            'metaphors': metaphors, # list of strings
            'mathConcepts': math_concepts, # list of strings
            'storyHistory': story_history # list of strings (contains previous scenes, new one will be added on next call)
        }
        
        response_model = StoryResponse.model_validate(scene_data)
        return jsonify(response_model.model_dump(by_alias=True))

    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/intro', methods=['GET'])
def get_intro():
    return jsonify({
        "questions": [
            "What are your favorite things to do? (e.g., sports, games, books, movies, etc.)",
            "What kind of story would you like to be part of? (e.g., fantasy, sci-fi, adventure)",
            "Who would you like to be in this story? (e.g., a wizard, a space explorer, a detective)",
            "What math topic would you like to learn about?"
        ]
    })

if __name__ == '__main__':
    if llm is None:
        print("LLM failed to initialize. The Flask app will run but LLM-dependent endpoints will fail.")
        print("Please ensure your GEMINI_API_KEY is correctly set in api.env and is valid.")
    # Make sure the port is an integer
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)