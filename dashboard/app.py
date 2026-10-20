import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.db.session_store import (
    init_db, get_concept_heatmap, list_recent_sessions, _conn,
)
from app.ingestion.loader import load_pdf
from app.ingestion.splitter import split_pages
from app.ingestion.embedder import embed_and_store
from app.agents.integrity import IntegrityAgent
from config import LECTURES_DIR

st.set_page_config(
    page_title="Instructor Dashboard",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    .kpi-card {
        background-color: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #4F46E5;
        text-align: center;
    }
    .kpi-title { color: #64748B; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-value { color: #1E293B; font-size: 32px; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: transparent;
        border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
        font-weight: 600; color: #64748B;
    }
    .stTabs [aria-selected="true"] { color: #4F46E5 !important; border-bottom: 3px solid #4F46E5 !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

init_db()

# ─── SIDEBAR: UPLOAD LECTURE ───────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 Admin Panel")
    st.divider()
    st.markdown("#### 📤 Upload Lecture")
    st.caption("Upload a PDF to automatically ingest it.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        if st.button("🚀 Process & Ingest", use_container_width=True):
            file_path = LECTURES_DIR / uploaded_file.name
            with st.spinner("Saving file..."):
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            with st.spinner("Extracting text..."):
                pages = load_pdf(file_path)
                chunks = split_pages(pages)
            if not chunks:
                st.error("❌ Failed to extract text. PDF might be scanned.")
            else:
                with st.spinner(f"Embedding {len(chunks)} chunks..."):
                    embed_and_store(chunks)
                st.success(f"✅ Ingested {len(chunks)} chunks!")
                st.cache_data.clear()
                st.rerun()

# ─── DATA LOADERS ──────────────────────────────────────────────────

@st.cache_data(ttl=5)
def load_heatmap():
    return get_concept_heatmap()

@st.cache_data(ttl=5)
def load_sessions():
    return list_recent_sessions(20)

@st.cache_data(ttl=5)
def load_all_answers():
    with _conn() as conn:
        rows = conn.execute("SELECT concept, attempt_number, is_correct, time_spent_seconds, hint_used, timestamp FROM answers ORDER BY answer_id DESC").fetchall()
    return [dict(r) for r in rows]

@st.cache_data(ttl=5)
def load_kpis():
    with _conn() as conn:
        sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
        answers = conn.execute("SELECT COUNT(*) as c FROM answers").fetchone()["c"]
        hints = conn.execute("SELECT COUNT(*) as c FROM answers WHERE hint_used = 1").fetchone()["c"]
        avg_time = conn.execute("SELECT AVG(time_spent_seconds) as t FROM answers").fetchone()["t"] or 0
    return {"sessions": sessions, "answers": answers, "hints": hints, "avg_time": round(avg_time, 1)}

@st.cache_data(ttl=5)
def load_integrity_flags():
    agent = IntegrityAgent(min_seconds=3.0, min_flags=1)
    return agent.analyze()

# ─── MAIN UI ───────────────────────────────────────────────────────

st.markdown("<h1 style='color: #1E293B;'>📊 Instructor Analytics</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B;'>Monitor student performance, identify knowledge gaps, and ensure assessment integrity.</p>", unsafe_allow_html=True)
st.write("")

# 1. KPI Cards
kpis = load_kpis()
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Sessions</div><div class="kpi-value">{kpis["sessions"]}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="kpi-card" style="border-left-color: #10B981;"><div class="kpi-title">Total Answers</div><div class="kpi-value">{kpis["answers"]}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="kpi-card" style="border-left-color: #F59E0B;"><div class="kpi-title">Hints Used</div><div class="kpi-value">{kpis["hints"]}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="kpi-card" style="border-left-color: #EF4444;"><div class="kpi-title">Avg Time (s)</div><div class="kpi-value">{kpis["avg_time"]}</div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

# 2. Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Concept Mastery", "🕒 Session History", "📈 Activity Timeline", "🚨 Integrity Agent"])

# ─── TAB 1: HEATMAP & CONCEPTS ─────────────────────────────────────
with tab1:
    heatmap = load_heatmap()
    if not heatmap:
        st.info("No answers recorded yet.")
    else:
        df = pd.DataFrame(heatmap)
        df = df.sort_values("failure_rate", ascending=False)
        
        if "lecture_file" in df.columns:
            df["label"] = df["concept"] + " (" + df["lecture_file"].astype(str).str.replace(".pdf", "", regex=False) + ")"
        else:
            df["label"] = df["concept"]
        
        st.markdown("### 🔥 Knowledge Gap Heatmap")
        st.caption("Red indicates students are struggling with this concept (needs re-teaching).")
        
        fig = go.Figure(data=go.Heatmap(
            z=[df["failure_rate"].tolist()], x=df["label"].tolist(), y=["Failure Rate"],
            colorscale=[[0.0, "#10B981"], [0.3, "#FBBF24"], [0.7, "#F97316"], [1.0, "#EF4444"]],
            zmin=0, zmax=1, text=[[f"{v*100:.0f}%" for v in df["failure_rate"]]],
            texttemplate="%{text}", textfont={"size": 14, "color": "white"}, colorbar=dict(title="Failure %"),
        ))
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(tickangle=-15, tickfont=dict(size=11)))
        st.plotly_chart(fig, width="stretch")
        
        st.divider()
        st.markdown("### 📋 Detailed Breakdown")
        
        df_display = df.copy()
        df_display["Failure Rate"] = df_display["failure_rate"].apply(lambda v: f"{v*100:.0f}%")
        df_display["Accuracy"] = (1 - pd.to_numeric(df["failure_rate"], errors="coerce")).apply(lambda v: f"{v*100:.0f}%")
        
        cols = ["concept", "total_attempts", "correct_attempts", "Failure Rate", "Accuracy", "avg_time_seconds"]
        new_cols = ["Concept", "Attempts", "Correct", "Failure Rate", "Accuracy", "Avg Time (s)"]
        if "lecture_file" in df_display.columns:
            cols.insert(1, "lecture_file"); new_cols.insert(1, "Lecture File")
        if "page_number" in df_display.columns:
            cols.insert(2, "page_number"); new_cols.insert(2, "Page")
            
        df_display = df_display[cols]
        df_display.columns = new_cols
        
        def color_row(row):
            fr = float(row["Failure Rate"].rstrip("%")) / 100
            if fr > 0.6: return ["background-color: #FEE2E2"] * len(row)
            if fr > 0.3: return ["background-color: #FEF3C7"] * len(row)
            return ["background-color: #D1FAE5"] * len(row)

        st.dataframe(df_display.style.apply(color_row, axis=1), width="stretch", hide_index=True)
        
        st.write("")
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report (CSV)", data=csv, file_name='knowledge_gap_report.csv', mime='text/csv')

# ─── TAB 2: RECENT SESSIONS ────────────────────────────────────────
with tab2:
    st.markdown("### 🕒 Recent Sessions")
    sessions = load_sessions()
    if not sessions:
        st.info("No sessions yet.")
    else:
        df_sessions = pd.DataFrame(sessions)
        df_sessions["Accuracy"] = (df_sessions["correct_count"] / df_sessions["total_questions"]).fillna(0).apply(lambda v: f"{v*100:.0f}%")
        df_sessions["Started"] = df_sessions["started_at"].str[:16]
        df_sessions = df_sessions[["session_id", "student_id", "lecture_file", "correct_count", "total_questions", "Accuracy", "Started"]]
        df_sessions.columns = ["Session ID", "Student", "Lecture File", "Correct", "Total", "Accuracy", "Started At"]
        st.dataframe(df_sessions, width="stretch", hide_index=True)

# ─── TAB 3: TIMELINE ───────────────────────────────────────────────
with tab3:
    st.markdown("### 📈 Answer Timeline")
    st.caption("Red dots indicate wrong answers, Green indicate correct answers. Larger dots mean later attempts.")
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
        fig2.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, width="stretch")
    else:
        st.info("No answers recorded yet.")

# ─── TAB 4: INTEGRITY AGENT ────────────────────────────────────────
with tab4:
    st.markdown("### 🚨 Integrity & Behavioral Analysis")
    st.caption("Detects potential AI-copying or cheating by analyzing response times. Answers selected correctly on the first try in under 3 seconds are flagged.")
    
    flags = load_integrity_flags()
    if not flags:
        st.success("✅ No suspicious activity detected. All response times look natural.")
    else:
        st.error(f"⚠️ Found **{len(flags)}** suspicious session(s). Immediate review recommended.")
        
        df_flags = pd.DataFrame(flags)
        st.dataframe(df_flags, width="stretch", hide_index=True)
        
        st.info("💡 **Recommendation:** In these sessions, the student's response time was too fast for human reading. Consider interviewing the student or re-testing them in a proctored environment.")

# Refresh Button
st.write("")
st.write("")
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()