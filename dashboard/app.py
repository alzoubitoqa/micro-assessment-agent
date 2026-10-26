import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from app.db.session_store import (
    init_db, get_concept_heatmap, list_recent_sessions, _conn,
)
from app.ingestion.loader import load_pdf
from app.ingestion.splitter import split_pages
from app.ingestion.embedder import embed_and_store
from app.agents.integrity import IntegrityAgent
from config import LECTURES_DIR

st.set_page_config(page_title="Instructor Dashboard | Itqan", page_icon="🎓", layout="wide")

# ─── CUSTOM CSS (PREMIUM DESIGN) ───────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #F8FAFC;
    }
    
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
        box-shadow: 4px 0 24px rgba(0,0,0,0.02);
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #1E293B, #4F46E5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        color: #64748B;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    .kpi-container {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: flex; flex-direction: column; align-items: flex-start;
    }
    .kpi-container:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .kpi-icon {
        font-size: 24px;
        margin-bottom: 12px;
        padding: 10px;
        border-radius: 12px;
        display: inline-block;
    }
    .kpi-title {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .kpi-value {
        color: #0F172A;
        font-size: 2rem;
        font-weight: 800;
        line-height: 1;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        color: #64748B;
        border: none !important;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #4F46E5 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-top: 2px solid #4F46E5;
        padding: 15px 0; text-align: center;
        font-size: 14px; color: #1E293B; font-weight: 600;
        z-index: 9999; box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
    }
    .custom-footer span { color: #4F46E5; font-weight: 800; font-size: 16px; }
    .block-container { padding-bottom: 100px; }
    </style>
""", unsafe_allow_html=True)

init_db()

# ─── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 20px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 20px;'>
            <h1 style='color: #4F46E5; font-weight: 900; font-size: 28px; margin: 0; letter-spacing: 1px;'>إِتْقان</h1>
            <p style='color: #94A3B8; font-size: 12px; margin-top: 4px; text-transform: uppercase; letter-spacing: 2px;'>Admin Panel</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### 📤 Upload Lecture")
    st.caption("Upload a PDF to automatically extract concepts and generate quizzes.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], label_visibility="collapsed")
    if uploaded_file is not None:
        # التعديل الأول: width='stretch'
        if st.button("🚀 Process & Ingest", width='stretch', type="primary"):
            file_path = LECTURES_DIR / uploaded_file.name
            with st.spinner("Saving file..."):
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            with st.spinner("Extracting text..."):
                pages = load_pdf(file_path); chunks = split_pages(pages)
            if not chunks: st.error("❌ Failed to extract text.")
            else:
                with st.spinner(f"Embedding {len(chunks)} chunks..."): embed_and_store(chunks)
                st.success(f"✅ Ingested {len(chunks)} chunks!")
                st.cache_data.clear(); st.rerun()

# ─── DATA LOADERS ──────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_heatmap(): return get_concept_heatmap()

@st.cache_data(ttl=5)
def load_sessions(): return list_recent_sessions(20)

@st.cache_data(ttl=5)
def load_all_answers():
    with _conn() as conn:
        rows = conn.execute("SELECT concept, attempt_number, is_correct, time_spent_seconds, hint_used, timestamp FROM answers ORDER BY answer_id DESC").fetchall()
    return [dict(r) for r in rows]

@st.cache_data(ttl=5)
def load_kpis():
    with _conn() as conn:
        s = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
        a = conn.execute("SELECT COUNT(*) as c FROM answers").fetchone()["c"]
        h = conn.execute("SELECT COUNT(*) as c FROM answers WHERE hint_used = 1").fetchone()["c"]
        t = conn.execute("SELECT AVG(time_spent_seconds) as t FROM answers").fetchone()["t"] or 0
    return {"sessions": s, "answers": a, "hints": h, "avg_time": round(t, 1)}

@st.cache_data(ttl=5)
def load_integrity_flags():
    agent = IntegrityAgent(min_seconds=3.0, min_flags=1)
    return agent.analyze()

# ─── MAIN UI ───────────────────────────────────────────────────────
st.markdown('<div class="main-title">Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Monitor student performance, identify knowledge gaps, and ensure assessment integrity.</div>', unsafe_allow_html=True)

kpis = load_kpis()
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f'''
        <div class="kpi-container">
            <div class="kpi-icon" style="background: #EEF2FF; color: #4F46E5;">📊</div>
            <div class="kpi-title">Total Sessions</div>
            <div class="kpi-value">{kpis["sessions"]}</div>
        </div>
    ''', unsafe_allow_html=True)

with c2:
    st.markdown(f'''
        <div class="kpi-container">
            <div class="kpi-icon" style="background: #ECFDF5; color: #10B981;">✅</div>
            <div class="kpi-title">Total Answers</div>
            <div class="kpi-value">{kpis["answers"]}</div>
        </div>
    ''', unsafe_allow_html=True)

with c3:
    st.markdown(f'''
        <div class="kpi-container">
            <div class="kpi-icon" style="background: #FEF3C7; color: #D97706;">💡</div>
            <div class="kpi-title">Hints Used</div>
            <div class="kpi-value">{kpis["hints"]}</div>
        </div>
    ''', unsafe_allow_html=True)

with c4:
    st.markdown(f'''
        <div class="kpi-container">
            <div class="kpi-icon" style="background: #FEE2E2; color: #EF4444;">⏱️</div>
            <div class="kpi-title">Avg Time (s)</div>
            <div class="kpi-value">{kpis["avg_time"]}</div>
        </div>
    ''', unsafe_allow_html=True)

st.write("")
st.write("")

# ─── TABS ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Concept Mastery", "🕒 Session History", "📈 Activity Timeline", "🚨 Integrity Agent"])

# ─── TAB 1: CONCEPT MASTERY ────────────────────────────────────────
with tab1:
    heatmap = load_heatmap()
    if not heatmap:
        st.info("No answers recorded yet.")
    else:
        df = pd.DataFrame(heatmap)
        df = df.sort_values("failure_rate", ascending=True)
        
        if "lecture_file" in df.columns:
            df["short_file"] = df["lecture_file"].astype(str).str.replace(".pdf", "", regex=False).str[:20]
            df["label"] = df["concept"] + " <span style='color:#94A3B8; font-size:12px;'>(" + df["short_file"] + ")</span>"
        else:
            df["label"] = df["concept"]
            
        st.markdown("### Knowledge Gap Analysis")
        st.caption("Red bars indicate concepts where students are struggling the most.")
        
        fig = px.bar(
            df, x="failure_rate", y="label", orientation='h',
            color="failure_rate", 
            color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"], 
            text=df["failure_rate"].apply(lambda v: f"{v*100:.0f}%"),
            labels={"failure_rate": "Failure Rate", "label": ""}
        )
        
        fig.update_layout(
            height=350 + (len(df) * 40),
            margin=dict(l=10, r=60, t=10, b=20), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            coloraxis_showscale=False,
            yaxis=dict(tickfont=dict(size=13, color="#334155", weight="bold"), showgrid=False, zeroline=False),
            xaxis=dict(tickformat=".0%", showgrid=True, gridcolor="#E2E8F0", zeroline=False, visible=False)
        )
        
        fig.update_traces(
            textposition='outside', 
            textfont=dict(color='#0F172A', size=14, weight='bold'),
            marker=dict(line=dict(width=0)), 
            width=0.6 
        )
        
        # التعديل الثاني: width='stretch'
        st.plotly_chart(fig, width='stretch')
        
        st.divider()
        
        st.markdown("### 📋 Detailed Breakdown")
        
        df_display = df.copy()
        df_display["Failure Rate"] = df_display["failure_rate"].apply(lambda v: f"{v*100:.0f}%")
        df_display["Accuracy"] = (1 - pd.to_numeric(df["failure_rate"], errors="coerce")).apply(lambda v: f"{v*100:.0f}%")
        
        cols = ["concept", "total_attempts", "correct_attempts", "Failure Rate", "Accuracy", "avg_time_seconds"]
        new_cols = ["Concept", "Attempts", "Correct", "Failure Rate", "Accuracy", "Avg Time (s)"]
        if "lecture_file" in df_display.columns:
            cols.insert(1, "lecture_file"); new_cols.insert(1, "Lecture File")
            
        df_display = df_display[cols]
        df_display.columns = new_cols
        
        def color_row(row):
            fr = float(row["Failure Rate"].rstrip("%")) / 100
            if fr > 0.6: return ["background-color: #FEE2E2; color: #991B1B; font-weight: bold"] * len(row)
            if fr > 0.3: return ["background-color: #FEF3C7; color: #92400E; font-weight: bold"] * len(row)
            return ["background-color: #D1FAE5; color: #065F46; font-weight: bold"] * len(row)

        # التعديل الثالث: width='stretch'
        st.dataframe(df_display.style.apply(color_row, axis=1), width='stretch', hide_index=True)
        
        st.write("")
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report (CSV)", data=csv, file_name='knowledge_gap_report.csv', mime='text/csv')

# ─── TAB 2: RECENT SESSIONS ────────────────────────────────────────
with tab2:
    st.markdown("### 🕒 Recent Sessions")
    sessions = load_sessions()
    if not sessions: st.info("No sessions yet.")
    else:
        df_sessions = pd.DataFrame(sessions)
        df_sessions["Accuracy"] = (df_sessions["correct_count"] / df_sessions["total_questions"]).fillna(0).apply(lambda v: f"{v*100:.0f}%")
        df_sessions["Started"] = df_sessions["started_at"].str[:16]
        df_sessions = df_sessions[["session_id", "student_id", "lecture_file", "correct_count", "total_questions", "Accuracy", "Started"]]
        df_sessions.columns = ["Session ID", "Student", "Lecture File", "Correct", "Total", "Accuracy", "Started At"]
        # التعديل الرابع: width='stretch'
        st.dataframe(df_sessions, width='stretch', hide_index=True)

# ─── TAB 3: TIMELINE ───────────────────────────────────────────────
with tab3:
    st.markdown("### 📈 Answer Timeline")
    answers = load_all_answers()
    if answers:
        df_ans = pd.DataFrame(answers)
        df_ans["timestamp"] = pd.to_datetime(df_ans["timestamp"])
        df_ans = df_ans.sort_values("timestamp")
        
        fig2 = px.scatter(
            df_ans, x="timestamp", y="time_spent_seconds", color="is_correct",
            color_discrete_map={0: "#EF4444", 1: "#10B981"},
            size="attempt_number", hover_data=["concept", "attempt_number"],
            labels={"time_spent_seconds": "Time (s)", "timestamp": "Time", "is_correct": "Correct"},
        )
        fig2.update_layout(
            height=450, margin=dict(l=10, r=10, t=10, b=40), 
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0")
        )
        # التعديل الخامس: width='stretch'
        st.plotly_chart(fig2, width='stretch')
    else: st.info("No answers recorded yet.")

# ─── TAB 4: INTEGRITY AGENT ────────────────────────────────────────
with tab4:
    st.markdown("### 🚨 Integrity & Behavioral Analysis")
    st.caption("Detects potential AI-copying by analyzing response times (<3 seconds).")
    flags = load_integrity_flags()
    if not flags: 
        st.success("✅ No suspicious activity detected. All response times look natural.")
    else:
        st.error(f"⚠️ Found **{len(flags)}** suspicious session(s).")
        # التعديل السادس: width='stretch'
        st.dataframe(pd.DataFrame(flags), width='stretch', hide_index=True)

st.write("")
st.write("")
if st.button("🔄 Refresh Data"):
    st.cache_data.clear(); st.rerun()

# ─── FOOTER ────────────────────────────────────────────────────────
st.markdown("""
    <div class="custom-footer">
        © 2026 <span>Team Itqan (إِتْقان)</span> &nbsp;|&nbsp; AI for Good Lab Hackathon - UAE
    </div>
""", unsafe_allow_html=True)