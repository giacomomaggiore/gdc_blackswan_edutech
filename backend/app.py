from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser
import json

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

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.8,
        google_api_key=api_key,
        max_output_tokens=2048,
        top_p=0.8,
        top_k=40,
        convert_system_message_to_human=True
    )
    logger.info("Google Gemini LLM initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None

# === Tools ===
@tool
def generate_story_chapter(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new chapter of the story based on the current state."""
    try:
        logger.info("Generating story chapter...")
        prompt = f"""You are a masterful storyteller and math educator who creates engaging, educational stories.
        Create a story chapter that:
        - Is immersive and captivating
        - Integrates mathematical concepts naturally
        - Uses clear, simple language for 10-12 year olds
        - Creates meaningful connections between story elements and mathematical thinking
        - Includes a question at the end that tests understanding of the math concept

        Generate a story chapter for:
        Character: {state['user_name']}
        Context: {state['user_context']}
        Math Topic: {state['topic']}
        Previous Story: {state.get('story_history', [])}
        Current Chapter: {state.get('counter', 0)}

        Return the response in this JSON format:
        {{
            "story": "The story chapter text",
            "question": "The question text",
            "choices": ["choice a", "choice b", "choice c"],
            "correct_answer": "The correct choice",
            "metaphor": "A metaphor connecting the story to the math concept"
        }}"""
        
        logger.info("Invoking LLM...")
        response = llm([HumanMessage(content=prompt)])
        response_text = response.content
        
        logger.info(f"Raw LLM response: {response_text}")
        
        # Clean the response and parse JSON
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        story_data = json.loads(response_text)
        
        logger.info(f"Parsed story data: {story_data}")
        
        # Update state
        state["story"] = story_data["story"]
        state["last_chapter"] = story_data["story"]
        state.setdefault("story_history", []).append(story_data["story"])
        state.setdefault("metaphors", []).append(story_data["metaphor"])
        state["correct_answer"] = story_data["correct_answer"]
        
        return story_data
        
    except Exception as e:
        logger.error(f"Error in generate_story_chapter: {str(e)}", exc_info=True)
        return {
            "error": "Failed to generate story chapter",
            "details": str(e)
        }

@tool
def check_answer(state: Dict[str, Any], answer: str) -> Dict[str, Any]:
    """Check if the user's answer is correct and update the score."""
    try:
        if answer.lower() == state.get("correct_answer", "").lower():
            state["score"] = state.get("score", 0) + 1
            return {"correct": True, "feedback": "Great job! That's correct!"}
        return {"correct": False, "feedback": "Not quite right. Try again!"}
    except Exception as e:
        logger.error(f"Error in check_answer: {str(e)}", exc_info=True)
        return {
            "error": "Failed to check answer",
            "details": str(e)
        }

# === Agent Setup ===
def create_story_agent():
    tools = [generate_story_chapter, check_answer]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a story-telling agent that creates educational math stories.
        Your goal is to create an engaging story that teaches math concepts through narrative.
        
        You have access to these tools:
        1. generate_story_chapter: Generates a new chapter of the story
        2. check_answer: Checks if a user's answer is correct
        
        When using generate_story_chapter:
        - Pass the current state as the first argument
        - The state should include: user_name, user_context, topic, story_history, counter
        
        When using check_answer:
        - Pass the current state as the first argument
        - Pass the user's answer as the second argument
        
        Always maintain the story's continuity and ensure the math concepts are properly integrated."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# === Flask Routes ===
@app.route('/api/generate-story', methods=['POST'])
def generate_story():
    try:
        logger.info("Starting story generation...")
        request_data = request.json or {}
        logger.info(f"Received request data: {request_data}")
        
        # Initialize state
        state = {
            "user_name": request_data.get("character", "adventurer"),
            "user_context": request_data.get("storyContext", "fantasy world"),
            "topic": request_data.get("mathTopic", "algebra"),
            "story": "",
            "story_history": [],
            "counter": 0,
            "score": 0
        }
        
        logger.info(f"Initial state: {state}")
        
        # Create and invoke agent
        agent = create_story_agent()
        result = agent.invoke({
            "input": "Generate the first chapter of the story",
            "chat_history": [],
            "state": state
        })
        
        logger.info(f"Agent result: {result}")
        
        # Format response
        response = {
            "sceneText": state["story"],
            "imageRef": "",
            "progress": 0.2,
            "questions": [{
                "prompt": result.get("question", "What would you like to do next?"),
                "choices": result.get("choices", ["Option A", "Option B", "Option C"]),
                "answer": result.get("correct_answer", "Option A"),
                "feedback": ["Try again!", "Not quite right!", "Keep going!"]
            }],
            "metaphor": result.get("metaphor", ""),
            "mathConcept": state["topic"],
            "finished": False,
            "score": state["score"],
            "state": state
        }
        
        logger.info("Successfully generated story response")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to generate story",
            "details": str(e)
        }), 500

@app.route('/api/progress-story', methods=['POST'])
def progress_story():
    try:
        data = request.json or {}
        logger.info(f"Received progress request: {data}")
        
        # Rehydrate state
        state = {
            **data.get("state", {}),
            "user_answer": data.get("choice", "")
        }
        
        # Create and invoke agent
        agent = create_story_agent()
        
        # Check answer
        answer_result = agent.invoke({
            "input": f"Check if the answer '{state['user_answer']}' is correct",
            "chat_history": [],
            "state": state
        })
        
        if answer_result.get("correct"):
            state["score"] += 1
        
        # Generate next chapter if not finished
        if state["counter"] < 2:
            chapter_result = agent.invoke({
                "input": "Generate the next chapter of the story",
                "chat_history": [],
                "state": state
            })
            
            state["counter"] += 1
            state["story_history"].append(chapter_result["story"])
            state["story"] = chapter_result["story"]
            
            response = {
                "sceneText": chapter_result["story"],
                "questions": [{
                    "prompt": chapter_result["question"],
                    "choices": chapter_result["choices"],
                    "answer": chapter_result["correct_answer"],
                    "feedback": ["Try again!", "Not quite right!", "Keep going!"]
                }],
                "metaphor": chapter_result["metaphor"],
                "mathConcept": state["topic"],
                "progress": (state["counter"] + 1) / 3,
                "finished": state["counter"] >= 2,
                "score": state["score"],
                "state": state
            }
            
            return jsonify(response)
            
        return jsonify({"error": "Story already finished"}), 400
        
    except Exception as e:
        logger.error(f"Error in progress_story: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to progress story",
            "details": str(e)
        }), 500

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
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)