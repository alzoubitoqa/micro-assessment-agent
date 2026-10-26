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
    page_title="Itqan AI Assessment",
    page_icon="🎓",
    layout="centered",
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&display=swap');
    
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    
    /* 1. الخلفية المتحركة الهادئة */
    .stApp {
        background: linear-gradient(-45deg, #f0f4f8, #e2e8f0, #ebf4ff, #f8fafc);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* 2. شعار إتقان */
    .itqan-logo { text-align: center; margin-top: 20px; margin-bottom: 30px; }
    .itqan-text {
        font-size: 4.5rem; font-weight: 900;
        background: -webkit-linear-gradient(45deg, #4f46e5, #9333ea, #ec4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: 2px; margin-bottom: 0px; line-height: 1.2;
    }
    .itqan-subtitle { color: #64748b; font-size: 1.1rem; font-weight: 400; letter-spacing: 1px; text-transform: uppercase; }
    
    /* 3. البطاقة الزجاجية */
    .glass-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.6);
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    /* 4. الأزرار */
    div.stButton > button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white; border-radius: 10px; border: none;
        padding: 12px 24px; font-size: 16px; font-weight: 600;
        transition: all 0.3s ease; width: 100%;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
        margin-top: 10px;
    }
    div.stButton > button:hover {
        transform: translateY(-2px); box-shadow: 0 0 20px rgba(124, 58, 237, 0.6);
    }
    
    /* 5. الفوتر */
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
        border-top: 2px solid #4F46E5; padding: 12px 0; text-align: center;
        font-size: 13px; color: #1E293B; font-weight: 600;
        z-index: 9999; box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
    }
    .custom-footer span { color: #4F46E5; font-weight: 800; font-size: 15px; }
    .block-container { padding-bottom: 80px; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

init_db()

# ─── STATE INIT ────────────────────────────────────────────────────
if "quiz_state" not in st.session_state: st.session_state.quiz_state = None
if "session_id" not in st.session_state: st.session_state.session_id = None
if "student_name" not in st.session_state: st.session_state.student_name = ""
if "start_time" not in st.session_state: st.session_state.start_time = None
if "graph" not in st.session_state: st.session_state.graph = build_graph()

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
        "session_id": session_id, "concept": concept, "difficulty": "medium",
        "max_attempts": 3, "question": None, "attempt": 0,
        "student_answer": None, "time_spent": 0.0, "hint_text": None,
        "is_correct": None, "done": False, "feedback": "",
    }
    with st.spinner("🤖 AI is preparing your question..."):
        state = st.session_state.graph.invoke(state)
    st.session_state.quiz_state = state
    st.session_state.start_time = time.time()
    st.rerun()

# ─── UI: START SCREEN ──────────────────────────────────────────────
if st.session_state.quiz_state is None:
    
    # عرض الشعار
    st.markdown("""
        <div class="itqan-logo">
            <div class="itqan-text">إِتْقان</div>
            <div class="itqan-subtitle">AI-Powered Formative Assessment</div>
        </div>
    """, unsafe_allow_html=True)
    
    # استخدام div بدلاً من form لكي تتحدث المفاهيم فوراً
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top: 0; color: #1e293b;'>🚀 Start Your Quiz</h3>", unsafe_allow_html=True)
    
    student_id = st.text_input("👤 Your Name / ID:", placeholder="Enter your name here...")
    
    lectures = list_available_lectures()
    if not lectures:
        st.error("No lectures available. Please ask your instructor.")
        st.stop()
        
    lecture_file = st.selectbox("📚 Select Lecture:", lectures)
    
    # هنا التحديث الفوري يحدث لأننا لسنا داخل form
    with st.spinner("Loading concepts..."):
        concepts = extract_concepts(lecture_file)
        
    concept_names = [c["name"] for c in concepts]
    concept_name = st.selectbox("🧠 Select Concept:", concept_names)
    
    st.write("")
    if st.button("Start Learning 🚀", type="primary"): # تم إزالة width هنا لأن CSS يجعله بعرض كامل
        if not student_id.strip():
            st.warning("⚠️ Please enter your name.")
        else:
            start_quiz(student_id, lecture_file, concept_name)
            
    st.markdown('</div>', unsafe_allow_html=True)

# ─── UI: QUIZ SCREEN ───────────────────────────────────────────────
else:
    state = st.session_state.quiz_state
    
    st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.9); padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); display: flex; justify-content: space-between; margin-bottom: 20px; border-left: 5px solid #4f46e5;">
            <span style="font-weight: 600; color: #334155;">👤 {st.session_state.student_name}</span>
            <span style="font-weight: 600; color: #4f46e5;">🧠 {state['concept']}</span>
        </div>
    """, unsafe_allow_html=True)

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
        if st.button("Take Another Quiz 🔄"): reset_quiz()
        st.stop()

    q = state["question"]
    attempt = state["attempt"]
    
    st.progress(attempt / state["max_attempts"], text=f"Attempt {attempt} of {state['max_attempts']}")
    st.write("")
    
    if state.get("hint_text"):
        st.info(f"💡 **Hint:** {state['hint_text']}")
        st.write("")

    # هنا نحتفظ بالـ form لكي لا يتم إرسال الإجابة إلا عند الضغط على الزر
    with st.form("answer_form"):
        st.markdown(f"<h3 style='color: #1e293b; line-height: 1.5;'>{q['question_text']}</h3>", unsafe_allow_html=True)
        st.write("")
        
        selected_option = st.radio("Choose the correct answer:", q["options"], index=None, label_visibility="collapsed")
        st.write("")
        
        submit_ans = st.form_submit_button("Submit Answer") # تم إزالة width
        
        if submit_ans:
            if selected_option is None:
                st.warning("⚠️ Please select an option.")
            else:
                elapsed = time.time() - st.session_state.start_time
                state["student_answer"] = selected_option
                state["time_spent"] = elapsed
                
                with st.spinner("Evaluating..."):
                    state = st.session_state.graph.invoke(state)
                    
                st.session_state.quiz_state = state
                st.session_state.start_time = time.time()
                st.rerun()

# ─── FOOTER ────────────────────────────────────────────────────────
st.markdown("""
    <div class="custom-footer">
        © 2026 <span>Team Itqan (إِتْقان)</span> &nbsp;|&nbsp; AI for Good Lab Hackathon - UAE
    </div>
""", unsafe_allow_html=True)