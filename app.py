import streamlit as st
from story_agent import StoryAgent

# Initialize session state
if 'story_state' not in st.session_state:
    st.session_state.story_state = None
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

# Page config
st.set_page_config(
    page_title="Storia Interattiva",
    page_icon="📚",
    layout="wide"
)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/storytelling.png", width=80)
    st.header("🎲 Parametri storia")
    user_name = st.text_input("👤 Nome del protagonista", "un nago guerriero")
    user_context = st.text_input("🌍 Ambientazione", "mordor del signore degli anelli")
    topic = st.text_input("📚 Argomento", "teorema di pitagora")
    if st.button("🚀 Inizia Nuova Storia", use_container_width=True):
        st.session_state.agent = StoryAgent()
        st.session_state.story_state = st.session_state.agent.start_story(
            user_name=user_name,
            user_context=user_context,
            topic=topic
        )
        st.session_state.user_input = ""
        st.success("Storia inizializzata!")
    st.markdown("---")
    if st.session_state.story_state:
        st.metric("🏆 Punteggio", st.session_state.story_state["score"])
        st.markdown(f"**Capitolo:** {st.session_state.story_state['chapter_number']}")
    st.markdown("<div style='font-size:12px;color:gray;'>Made with ❤️ by EduTech</div>", unsafe_allow_html=True)

# --- Main Layout ---
st.title("📚 Storia Interattiva")
st.markdown("<span style='font-size:20px;'>Crea una storia personalizzata e rispondi alle domande per progredire!</span>", unsafe_allow_html=True)

if st.session_state.story_state:
    col1, col2 = st.columns([3, 1])
    with col1:
        with st.container():
            st.markdown("""
                <div style='background: #f9f9fa; border-radius: 16px; padding: 2rem 2rem 1rem 2rem; box-shadow: 0 2px 8px #0001;'>
                    <h3 style='color:#3b3b3b;'>📖 La tua storia</h3>
                    <div style='font-size: 1.1rem; color: #222; line-height: 1.7;'>
                        {0}
                    </div>
                </div>
            """.format(st.session_state.story_state["story"].replace("\n", "<br>")), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""
                <div style='background: #eaf6ff; border-radius: 12px; padding: 1.2rem 1.5rem; box-shadow: 0 1px 4px #0001;'>
                    <h4 style='color:#1a73e8;'>❓ Domanda attuale</h4>
                    <div style='font-size: 1.08rem; color: #222; line-height: 1.6;'>
                        {0}
                    </div>
                </div>
            """.format(st.session_state.story_state["current_question"].replace("\n", "<br>")), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("<div style='font-size:1.1rem; color:#444;'>Rispondi per continuare la storia:</div>", unsafe_allow_html=True)
            answer = st.text_input("La tua risposta (a, b, o c):", value=st.session_state.user_input, key="answer_input").lower()
            st.session_state.user_input = answer
            send_col, _ = st.columns([1, 5])
            with send_col:
                if st.button("Invia Risposta", use_container_width=True):
                    if answer in ['a', 'b', 'c']:
                        st.session_state.story_state = st.session_state.agent.process_answer(
                            st.session_state.story_state,
                            answer
                        )
                        st.session_state.user_input = ""
                        st.experimental_rerun()
                    elif answer:
                        st.warning("Per favore, inserisci 'a', 'b' o 'c'", icon="⚠️")
    with col2:
        st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div style='background: #fffbe6; border-radius: 12px; padding: 1.2rem 1.5rem; box-shadow: 0 1px 4px #0001; margin-bottom: 1.5rem;'>
                <span style='font-size:1.2rem;'>📅 <b>Capitolo</b>: {0}</span><br>
                <span style='font-size:1.2rem;'>🏆 <b>Punteggio</b>: {1}</span>
            </div>
        """.format(st.session_state.story_state['chapter_number'], st.session_state.story_state['score']), unsafe_allow_html=True)
else:
    st.info("👈 Usa la barra laterale per iniziare una nuova storia!", icon="📝") 