import streamlit as st
from story_agent import StoryAgent

# Initialize session state
if 'story_state' not in st.session_state:
    st.session_state.story_state = None
if 'agent' not in st.session_state:
    st.session_state.agent = None

# Page config
st.set_page_config(
    page_title="Storia Interattiva",
    page_icon="📚",
    layout="wide"
)

# Title
st.title("📚 Storia Interattiva")
st.markdown("Crea una storia personalizzata e rispondi alle domande per progredire!")

# Sidebar for initialization
with st.sidebar:
    st.header("Inizializza la Storia")
    
    # Story parameters
    user_name = st.text_input("Nome del protagonista", "un nago guerriero")
    user_context = st.text_input("Ambientazione", "mordor del signore degli anelli")
    topic = st.text_input("Argomento", "teorema di pitagora")
    
    # Initialize button
    if st.button("Inizia Nuova Storia"):
        # Initialize agent (API key is now managed in story_agent.py)
        st.session_state.agent = StoryAgent()
        # Start new story
        st.session_state.story_state = st.session_state.agent.start_story(
            user_name=user_name,
            user_context=user_context,
            topic=topic
        )
        st.success("Storia inizializzata!")

# Main content area
if st.session_state.story_state:
    # Display current chapter as narrative text
    st.write(st.session_state.story_state["last_chapter"])
    
    # Display score
    st.sidebar.metric("Punteggio", st.session_state.story_state["score"])
    
    # Answer input
    answer = st.text_input("La tua risposta (a, b, o c):").lower()
    
    if answer in ['a', 'b', 'c']:
        if st.button("Invia Risposta"):
            # Process answer and get next chapter
            st.session_state.story_state = st.session_state.agent.process_answer(
                st.session_state.story_state,
                answer
            )
            st.experimental_rerun()
    elif answer:
        st.warning("Per favore, inserisci 'a', 'b', o 'c'")
else:
    st.info("👈 Usa la barra laterale per iniziare una nuova storia!") 