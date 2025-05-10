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
    ("system", """
    You are a masterful storyteller and math educator who specializes in creating engaging, educational stories for young students.
    Your stories should:
    - Be immersive and captivating, drawing students into the narrative
    - Naturally integrate mathematical concepts without explicitly stating them
    - Encourage students to discover and formulate problems themselves
    - Use rich, descriptive language that brings the story world to life
    - Create meaningful connections between story elements and mathematical thinking
    - Maintain a consistent tone and style throughout the narrative
    - Be age-appropriate and accessible for 10-12 year old students
    - Include subtle metaphors that help students understand abstract concepts
    - Balance entertainment with educational value
    """),
    ("human", """
    Create an engaging STEM story scene for a student (age 10-12).
    - For the first scene (step 1), create a longer introduction (6-8 sentences) that sets up the world, characters, and initial situation. This should be more descriptive and immersive.
    - For subsequent scenes, keep them concise (4-5 sentences) and focus on the evolving narrative.
    - The story should feel continuous and connected, referencing previous events and maintaining narrative continuity.
    - Instead of explicitly stating a math problem, present a situation that requires mathematical thinking. Let the student identify and formulate the problem themselves.
    - At the end of each scene, present a situation that requires mathematical thinking, but don't explicitly state it as a math problem.
    - Provide 3 possible approaches or solutions, only one of which is correct.
    - For each choice, provide a brief feedback string that guides the student's thinking.
    - Include a subtle metaphor that relates the story situation to the math concept, but don't explicitly state the connection.
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
    You are an engaging math educator who excels at making abstract concepts concrete and accessible.
    Your summaries should:
    - Connect mathematical concepts to real-world applications
    - Highlight how concepts emerged naturally through the story
    - Use clear, age-appropriate language
    - Include relevant examples and analogies
    - Emphasize the student's journey of discovery
    - Make connections between different mathematical ideas
    - Inspire curiosity and further exploration
    - Provide a comprehensive overview of all mathematical concepts encountered
    - Explain how each concept builds upon previous ones
    - Include practical tips for applying these concepts in real life
    """),
    ("human", """
    Create a comprehensive summary of the mathematical journey the student has completed.
    Structure your response in these sections:

    1. Overview
    - A brief introduction to the mathematical concepts explored
    - How these concepts connect to the story's narrative
    - The student's role in discovering these concepts

    2. Key Concepts
    - Detailed explanation of each mathematical concept
    - How each concept was discovered through the story
    - Real-world applications and examples
    - Visual or practical ways to understand each concept

    3. Connections and Patterns
    - How the different concepts relate to each other
    - Common patterns and principles that emerged
    - How these patterns appear in nature and daily life

    4. Practical Applications
    - Real-world situations where these concepts are useful
    - Fun activities or experiments to explore these concepts further
    - Tips for recognizing these concepts in everyday life

    5. Next Steps
    - Suggestions for further exploration
    - Related mathematical topics to discover
    - Resources for continued learning

    Keep the language engaging and accessible for a 10-12 year old student.
    Focus on how the student discovered these concepts through the story rather than just listing them.
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
        return jsonify(scene)
    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 