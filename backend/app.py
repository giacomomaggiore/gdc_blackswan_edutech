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
    temperature=0.9,
    google_api_key=api_key,
    max_output_tokens=2048,
    top_p=0.8,
    top_k=40,
    convert_system_message_to_human=True
)

# Prompt templates
story_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a masterful storyteller and math educator who specializes in creating engaging, educational stories for young students.
    Your stories should:
    - Be immersive and captivating, drawing students into the narrative
    - Naturally integrate mathematical concepts without explicitly stating them
    - Encourage students to discover and formulate problems themselves
    - Use clear, simple, age-appropriate language for 10-12 year olds
    - Keep the story concise and easy to follow
    - Create meaningful connections between story elements and mathematical thinking
    - Maintain a consistent tone and style throughout the narrative
    - Include subtle metaphors that help students understand abstract concepts
    - Balance entertainment with educational value
    - The story must always stay focused on the math topic: {math_topic}.
    """),
    ("human", """
    Create a short, simple STEM story scene for a student (age 10-12).
    - For the first scene (step 1), write a brief introduction (3-4 sentences) that sets up the world, characters, and initial situation. Make it easy to understand.
    - For subsequent scenes, keep them very concise (2-3 sentences) and focus on the evolving narrative.
    - The story should feel continuous and connected, referencing previous events and maintaining narrative continuity.
    - Instead of explicitly stating a math problem, present a situation that requires mathematical thinking. Let the student identify and formulate the problem themselves.
    - At the end of each scene, present a situation that requires mathematical thinking, but don't explicitly state it as a math problem.
    - Provide 3 possible approaches or solutions, only one of which is correct.
    - For each choice, provide a brief feedback string that guides the student's thinking.
    - Include a subtle metaphor that relates the story situation to the math concept, but don't explicitly state the connection.
    - The story must always stay focused on the math topic: {math_topic}.
    - Return ONLY a JSON object in this format:
    {{
      "sceneText": "...",
      "imageRef": "...",
      "progress": 0.2,
      "questions": [
        {{
          "prompt": "...",
          "choices": ["...", "...", "..."],
          "answer": "...",
          "feedback": ["...", "...", "..."]
        }}
      ],
      "metaphor": "...",
      "mathConcept": "...",
      "finished": false,
      "score": 0
    }}
    The math topic is: {math_topic}
    The story context is: {story_context}
    The main character is: {character}
    The current step is: {step}
    Respond with ONLY the JSON object, no explanation or extra text.
    """)
])

# Add a prompt for advice generation
advice_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a supportive and encouraging math tutor who specializes in helping students understand mathematical concepts through their own discoveries.
    Your feedback should:
    - Focus on the student's problem-solving approach rather than just the final answer
    - Highlight the positive aspects of their thinking
    - Guide them toward deeper understanding
    - Connect their attempts to the underlying mathematical concepts
    - Maintain an encouraging and positive tone
    - Provide concrete, actionable advice for improvement
    """),
    ("human", """
    Given a list of missed questions, the student's answers, and the correct answers, write a short, encouraging summary for the student. For each missed question, provide a concrete explanation of the math concept and advice on how to improve. End with a positive message.
    Focus on the student's problem-solving approach rather than just the final answer.
    Missed questions:
    {missed}
    """)
])

# Add a prompt for theoretical summary
theory_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are an engaging math educator who explains key ideas in a few words for 10-12 year olds.
    Your summaries should:
    - Be very short and clear
    - Use simple, age-appropriate language
    - List only the most important concepts
    """),
    ("human", """
    Write a very short summary of the main math ideas from this story for a 10-12 year old.
    - List the key concepts you learned
    - Keep it simple and fun
    Math topic: {math_topic}
    Story metaphors: {metaphors}
    """)
])

# Add a prompt for math principle summary
principle_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a math teacher who explains core mathematical principles in a simple, clear way for 10-12 year olds.
    Your explanations should:
    - Be short, clear, and support markdown and LaTeX-style formulas (use $...$ for math)
    - Use a concrete example and a formula
    - Focus on the main principle behind the story's math topic
    - Make it memorable and practical
    - Add a brief theoretical explanation
    """),
    ("human", """
    Write a short, clear explanation of the main mathematical principle used in this adventure. Use markdown and LaTeX-style formulas (e.g., $x+3=7$). Give a concrete example and a formula. Add a brief theoretical explanation. For example, if the story is about equations, explain why multiplying both sides by the same number keeps the equation valid.
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
        math_topic = data.get('mathTopic')
        if not math_topic or not math_topic.strip():
            math_topic = 'algebra'
        step = 1
        chain = story_prompt | llm | StrOutputParser()
        story_json = chain.invoke({
            "math_topic": math_topic,
            "story_context": story_context,
            "character": character,
            "step": step
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
        scene['step'] = step
        scene['answers'] = []
        scene['finished'] = False
        scene['metaphors'] = [scene.get('metaphor', '')]
        scene['mathConcepts'] = [scene.get('mathConcept', '')]
        scene['storyHistory'] = [scene.get('sceneText', '')]
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
        math_topic = data.get('mathTopic')
        prev_scene = data.get('currentScene', {})
        step = prev_scene.get('step', 1) + 1
        score = prev_scene.get('score', 0)
        answers = prev_scene.get('answers', [])
        metaphors = prev_scene.get('metaphors', [])
        math_concepts = prev_scene.get('mathConcepts', [])
        story_history = prev_scene.get('storyHistory', [])
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
        # Track story history
        if prev_scene.get('sceneText'):
            story_history.append(prev_scene.get('sceneText'))
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
                "metaphors": "\n".join(metaphors),
                "story_history": "\n".join(story_history),
                "answers": json.dumps(answers)
            })
            # Generate principle summary
            principle_chain = principle_prompt | llm | StrOutputParser()
            principle_summary = principle_chain.invoke({
                "math_topic": math_topic,
                "metaphors": "\n".join(metaphors),
                "story_history": "\n".join(story_history),
                "answers": json.dumps(answers)
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
                'principleSummary': principle_summary,
                'metaphors': metaphors,
                'mathConcepts': math_concepts,
                'storyHistory': story_history
            })
        # Otherwise, generate next scene
        chain = story_prompt | llm | StrOutputParser()
        story_json = chain.invoke({
            "math_topic": math_topic,
            "story_context": story_context,
            "character": character,
            "step": step
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
        scene['storyHistory'] = story_history + [scene.get('sceneText', '')]
        return jsonify(scene)
    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 