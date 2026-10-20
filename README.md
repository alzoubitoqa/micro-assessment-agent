# 🎓 Micro-Assessment AI Agent

An intelligent, proactive formative assessment system that transforms academic evaluation from stressful, spaced-out exams into continuous, adaptive, and interactive learning.

## 🚀 The Pitch
Instructors often discover students' lack of understanding only after midterms or finals. This system uses a **Multi-Agent AI Architecture** to analyze lecture content instantly, generate personalized micro-quizzes, adapt to student performance in real-time, and provide instructors with a live "Knowledge Gap Heatmap" before it's too late.

## ✨ Key Features
- **📄 Dynamic RAG Generation:** Automatically ingests uploaded PDF lectures, extracts core concepts, and generates context-aware questions (Zero Hallucination via a Validator Agent).
- **🧠 Adaptive Feedback Loop (LangGraph):** If a student answers wrong, the agent provides a contextual hint. If they fail again, it simplifies the question.
- **🚨 Integrity Agent:** Analyzes response times to detect suspiciously fast answers (e.g., AI copying) and flags them for the instructor.
- **📊 Instructor Dashboard:** A beautiful, real-time analytics dashboard featuring a color-coded Heatmap, session tracking, and CSV export capabilities.
- **🎓 Student Portal:** A clean, distraction-free interface for students to take quizzes and receive immediate feedback.

## 🛠️ Tech Stack
- **Frontend/UI:** Streamlit (Instructor Dashboard & Student Portal)
- **Agent Orchestration:** LangGraph (State Machine for adaptive routing)
- **LLM Engine:** Groq API (Llama-3.3-70b-versatile) for ultra-fast generation.
- **Embeddings:** Sentence-Transformers (`all-MiniLM-L6-v2`) running locally.
- **Vector Database:** ChromaDB (Local persistent storage).
- **Relational Database:** SQLite (Session & Answer tracking).

## ⚙️ Quick Start Guide

### 1. Prerequisites
Ensure you have **Python 3.12** installed.

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-link>
cd micro-assessment-agent

# Create and activate virtual environment
python3.12 -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

3. Environment Setup
Create a .env file in the root directory and add your Groq API key:

env
GROQ_API_KEY=gsk_your_api_key_here
LLM_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=400
CHUNK_OVERLAP=60
TOP_K_RETRIEVAL=5
VALIDATE_QUESTIONS=true
4. Running the Application
You need two terminal windows to run both interfaces simultaneously.

Terminal 1: Instructor Dashboard

bash
streamlit run dashboard/app.py
(Access at: http://localhost:8501)

Terminal 2: Student Portal

bash
streamlit run dashboard/student_ui.py --server.port 8502
(Access at: http://localhost:8502)

🎬 How to Demo (For Hackathon Judges)
Upload: On the Instructor Dashboard (8501), use the sidebar to upload a lecture PDF. Watch as the system extracts and embeds it.

Take a Quiz: On the Student Portal (8502), enter a name, select the lecture, and start the quiz.

Experience Adaptation: Answer a question incorrectly to see the AI Agent generate a smart hint. Fail again to see it simplify the question.

View Analytics: Go back to the Dashboard and click Refresh Data. Watch the Heatmap update instantly to show the Knowledge Gap.

Test Integrity: Take another quiz on the Student Portal, but answer correctly in under 3 seconds. Go back to the Dashboard and check the 🚨 Integrity Agent tab to see the red flag!

📂 Project Structure
text
micro-assessment-agent/
├── app/
│   ├── agents/          # AI Agents (Generator, Validator, Adaptive, Integrity)
│   ├── db/              # SQLite Session Store
│   ├── graph/           # LangGraph State Machine
│   ├── ingestion/       # PDF loaders and embedders
│   └── retrieval/       # ChromaDB search logic
├── dashboard/           # Streamlit UI (app.py & student_ui.py)
├── data/                # Local storage (PDFs, ChromaDB, SQLite)
├── scripts/             # CLI tools for testing
├── requirements.txt
└── README.md