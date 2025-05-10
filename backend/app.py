from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
import json, re

# Load environment variables
load_dotenv('api.env')

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangChain Gemini model
api_key = os.getenv('GEMINI_API_KEY')
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.7,
    google_api_key=api_key,
    max_output_tokens=2048,
    top_p=0.8,
    top_k=40,
    convert_system_message_to_human=True
)

# Prompt templates
story_prompt = ChatPromptTemplate.from_messages([
    ("human", """
    You are a creative storyteller and math educator. Create a short, engaging STEM story scene for a student (age 10-12).
    - The story should be concise (max 4 sentences), immersive, and include a math challenge as part of the narrative.
    - The story should feel like it is evolving and continuous, not a disconnected scene. Reference previous events and maintain narrative continuity.
    - At the end, ask a math question as part of the story, not as a quiz.
    - Provide 3 answer choices, only one of which is correct.
    - For each choice, provide a brief feedback string.
    - Include a metaphor that relates the story situation to the math concept.
    - Return ONLY a JSON object in this format:
    {{
      \"sceneText\": \"...\",
      \"imageRef\": \"...\",
      \"progress\": 0.2,
      \"questions\": [
        {{
          \"prompt\": \"...\",
          \"choices\": [\"...\", \"...\", \"...\"],
          \"answer\": \"...\",
          \"feedback\": [\"...\", \"...\", \"...\"]
        }}
      ],
      \"metaphor\": \"...\",
      \"mathConcept\": \"...\",
      \"finished\": false,
      \"score\": 0
    }}
    The math topic is: {math_topic}
    The story context is: {story_context}
    The main character is: {character}
    Respond with ONLY the JSON object, no explanation or extra text.
    """)
])

# Add a prompt for advice generation
advice_prompt = ChatPromptTemplate.from_messages([
    ("human", """
    You are a helpful math tutor. Given a list of missed questions, the student's answers, and the correct answers, write a short, encouraging summary for the student. For each missed question, provide a concrete explanation of the math concept and advice on how to improve. End with a positive message.
    Missed questions:
    {missed}
    """)
])

# Add a prompt for theoretical summary
theory_prompt = ChatPromptTemplate.from_messages([
    ("human", """
    You are a math educator. Create a clear, concise summary of the key theoretical concepts covered in this story.
    Include:
    1. The main mathematical concepts
    2. How they were represented in the story
    3. Real-world applications
    4. Key formulas or principles (if applicable)
    Keep it engaging and accessible for a 10-12 year old student.
    Math topic: {math_topic}
    Story metaphors: {metaphors}
    """)
])

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

@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    try:
        data = request.json
        story_context = data.get('storyContext', 'fantasy world')
        character = data.get('character', 'adventurer')
        math_topic = data.get('mathTopic', 'algebra')
        chain = story_prompt | llm | StrOutputParser()
        story_json = chain.invoke({
            "math_topic": math_topic,
            "story_context": story_context,
            "character": character
        })
        try:
            scene = json.loads(story_json)
        except Exception:
            match = re.search(r'({[\s\S]*})', story_json)
            if match:
                scene = json.loads(match.group(1))
            else:
                logger.error(f"Failed to extract JSON from: {story_json}")
                return jsonify({'error': 'Failed to parse story from LLM.', 'llm_raw_response': story_json}), 500
        # Initialize progress tracking
        scene['progress'] = 0.2
        scene['score'] = 0
        scene['step'] = 1
        scene['answers'] = []
        scene['finished'] = False
        scene['metaphors'] = [scene.get('metaphor', '')]
        scene['mathConcepts'] = [scene.get('mathConcept', '')]
        return jsonify(scene)
    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    try:
        data = request.json
        story_context = data.get('storyContext', 'fantasy world')
        character = data.get('character', 'adventurer')
        math_topic = data.get('mathTopic', 'algebra')
        prev_scene = data.get('currentScene', {})
        step = prev_scene.get('step', 1) + 1
        score = prev_scene.get('score', 0)
        answers = prev_scene.get('answers', [])
        metaphors = prev_scene.get('metaphors', [])
        math_concepts = prev_scene.get('mathConcepts', [])
        user_choice = data.get('choice')
        correct_answer = prev_scene.get('questions', [{}])[0].get('answer')
        question_prompt = prev_scene.get('questions', [{}])[0].get('prompt')
        # Track answers
        if user_choice is not None:
            answers.append({
                'question': question_prompt,
                'your_answer': user_choice,
                'correct_answer': correct_answer
            })
            if user_choice == correct_answer:
                score += 1
        # If finished
        if step > 5:
            # Build missed questions list
            wrong = [a for a in answers if a['your_answer'] != a['correct_answer']]
            if wrong:
                missed_str = "\n".join([
                    f"Q: {a['question']}\nYour answer: {a['your_answer']}\nCorrect answer: {a['correct_answer']}" for a in wrong
                ])
                advice_chain = advice_prompt | llm | StrOutputParser()
                advice = advice_chain.invoke({"missed": missed_str})
            else:
                advice = "You got all questions correct! Great job!"

            # Generate theoretical summary
            theory_chain = theory_prompt | llm | StrOutputParser()
            theory_summary = theory_chain.invoke({
                "math_topic": math_topic,
                "metaphors": "\n".join(metaphors)
            })

            return jsonify({
                'sceneText': advice,
                'imageRef': '',
                'progress': 1.0,
                'questions': [],
                'finished': True,
                'score': score,
                'answers': answers,
                'step': step,
                'theorySummary': theory_summary,
                'metaphors': metaphors,
                'mathConcepts': math_concepts
            })
        # Otherwise, generate next scene
        chain = story_prompt | llm | StrOutputParser()
        story_json = chain.invoke({
            "math_topic": math_topic,
            "story_context": story_context,
            "character": character
        })
        try:
            scene = json.loads(story_json)
        except Exception:
            match = re.search(r'({[\s\S]*})', story_json)
            if match:
                scene = json.loads(match.group(1))
            else:
                logger.error(f"Failed to extract JSON from: {story_json}")
                return jsonify({'error': 'Failed to parse story from LLM.', 'llm_raw_response': story_json}), 500
        scene['progress'] = min(1.0, step / 5)
        scene['score'] = score
        scene['step'] = step
        scene['answers'] = answers
        scene['finished'] = False
        scene['metaphors'] = metaphors + [scene.get('metaphor', '')]
        scene['mathConcepts'] = math_concepts + [scene.get('mathConcept', '')]
        return jsonify(scene)
    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 