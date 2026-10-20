import json
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL
from app.retrieval.retriever import retrieve
from app.models.schemas import Question

_client = Groq(api_key=GROQ_API_KEY)

HINT_PROMPT = """You are a teaching assistant. The student answered the following question incorrectly.
Provide a 2-sentence hint that does NOT reveal the answer directly, but guides the student toward the correct concept.
The lecture and question are in English. The hint MUST be in English.

Question: {question_text}
Options: {options}
Student's answer: {student_answer}

Context:
{context}

Hint:"""

SIMPLIFY_PROMPT = """You are a teaching assistant. The student is still struggling with the following question after receiving a hint.
Rewrite the question to be simpler and more direct, WITHOUT revealing the answer.
Use simpler vocabulary and focus on the core concept.

Original question: {question_text}
Options: {options}

Return ONLY valid JSON:
{{
  "question_text": "...",
  "options": ["...", "...", "...", "..."],
  "correct_answer": "..."
}}"""


def generate_hint(q: Question, student_answer: str) -> str:
    chunks = retrieve(q.concept)
    context = "\n\n".join(c["text"] for c in chunks)
    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": HINT_PROMPT.format(
            question_text=q.question_text, options=q.options,
            student_answer=student_answer, context=context,
        )}],
    )
    return resp.choices[0].message.content.strip()


def simplify_question(q: Question) -> Question:
    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": SIMPLIFY_PROMPT.format(
            question_text=q.question_text, options=q.options,
        )}],
    )
    data = json.loads(resp.choices[0].message.content)
    return Question(
        question_id=q.question_id + "_simple",
        concept=q.concept,
        difficulty="easy",
        question_text=data["question_text"],
        options=data["options"],
        correct_answer=data["correct_answer"],
        explanation=q.explanation,
        source_chunk_ids=q.source_chunk_ids,
    )