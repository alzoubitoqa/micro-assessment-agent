import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from app.db.session_store import (
    init_db, create_session, end_session, get_session_stats,
)
from app.graph.quiz_graph import build_graph
from app.agents.concept_extractor import extract_concepts, list_available_lectures

# ─── CONFIG & CUSTOM CSS ───────────────────────────────────────────
st.set_page_config(
    page_title="AI Assessment",
    page_icon="🎓",
    layout="centered",
)

# حقن CSS لجعل الواجهة تبدو احترافية
st.markdown("""
    <style>
    /* الخلفية العامة */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* تنسيق الأزرار */
    div.stButton > button:first-child {
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #4338CA;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    }
    
    /* تنسيق البطاقات (Cards) */
    div[data-testid="stVerticalBlock"] > div:has(div.stRadio) {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E5E7EB;
    }
    
    /* تنسيق العناوين */
    h1, h2, h3 {
        color: #1F2937;
        font-family: 'Inter', sans-serif;
    }
    
    /* إخفاء الشريط العلوي الافتراضي */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

init_db()

# ─── STATE INIT ────────────────────────────────────────────────────
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────
def reset_quiz():
    st.session_state.quiz_state = None
    st.session_state.session_id = None
    st.session_state.start_time = None
    st.rerun()

def start_quiz(student_id, lecture_file, concept):
    session_id = create_session(student_id, lecture_file)
    st.session_state.session_id = session_id
    st.session_state.student_name = student_id
    
    state = {
        "session_id": session_id,
        "concept": concept,
        "difficulty": "medium",
        "max_attempts": 3,
        "question": None,
        "attempt": 0,
        "student_answer": None,
        "time_spent": 0.0,
        "hint_text": None,
        "is_correct": None,
        "done": False,
        "feedback": "",
    }
    
    with st.spinner("🤖 AI is preparing your question from the lecture..."):
        state = st.session_state.graph.invoke(state)
        
    st.session_state.quiz_state = state
    st.session_state.start_time = time.time()
    st.rerun()

# ─── UI: START SCREEN ──────────────────────────────────────────────
if st.session_state.quiz_state is None:
    st.markdown("<h1 style='text-align: center;'>🎓 AI Assessment Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Adaptive Formative Assessment powered by AI</p>", unsafe_allow_html=True)
    st.write("") # Spacer

    with st.container():
        with st.form("start_form"):
            st.subheader("🚀 Start Your Quiz")
            student_id = st.text_input("👤 Your Name / ID:", placeholder="e.g., Toqa")
            
            lectures = list_available_lectures()
            if not lectures:
                st.error("No lectures available. Please ask your instructor to upload one.")
                st.stop()
                
            lecture_file = st.selectbox("📚 Select Lecture:", lectures)
            
            with st.spinner("Loading concepts..."):
                concepts = extract_concepts(lecture_file)
                
            concept_names = [c["name"] for c in concepts]
            concept_name = st.selectbox("🧠 Select Concept to be tested on:", concept_names)
            
            submit = st.form_submit_button("🚀 Start Quiz")
            
            if submit:
                if not student_id.strip():
                    st.warning("⚠️ Please enter your name.")
                else:
                    start_quiz(student_id, lecture_file, concept_name)

# ─── UI: QUIZ SCREEN ───────────────────────────────────────────────
else:
    state = st.session_state.quiz_state
    
    # Top Bar (Header)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"👤 **Student:** {st.session_state.student_name}")
    with col2:
        st.markdown(f"🧠 **Concept:** {state['concept']}")
    
    st.divider()

    # If quiz is done
    if state.get("done"):
        if state.get("is_correct"):
            st.balloons()
            st.success(f"### 🎉 Excellent!\n{state['feedback']}")
        else:
            st.error(f"### 📚 Keep Learning\n{state['feedback']}")
            
        end_session(st.session_state.session_id)
        stats = get_session_stats(st.session_state.session_id)
        
        st.info(f"Final Result: **{stats['correct_count']}** correct out of **{stats['total_questions']}** question(s).")
        
        st.write("")
        if st.button("🔄 Take Another Quiz"):
            reset_quiz()
        st.stop()

    # If waiting for answer
    q = state["question"]
    
    # Progress bar
    attempt = state["attempt"]
    max_attempts = state["max_attempts"]
    st.progress(attempt / max_attempts, text=f"Attempt {attempt} of {max_attempts}")
    st.write("")
    
    # Show Hint if exists
    if state.get("hint_text"):
        st.info(f"💡 **Hint:** {state['hint_text']}")
        st.write("")

    # Question Card
    with st.container():
        st.markdown(f"### Q: {q['question_text']}")
        st.write("")
        
        options = q["options"]
        selected_option = st.radio("Choose the correct answer:", options, index=None)
        
        st.write("")
        if st.button("Submit Answer", type="primary"):
            if selected_option is None:
                st.warning("⚠️ Please select an option first.")
            else:
                elapsed = time.time() - st.session_state.start_time
                
                state["student_answer"] = selected_option
                state["time_spent"] = elapsed
                
                with st.spinner("Checking..."):
                    state = st.session_state.graph.invoke(state)
                    
                st.session_state.quiz_state = state
                st.session_state.start_time = time.time()
                st.rerun()