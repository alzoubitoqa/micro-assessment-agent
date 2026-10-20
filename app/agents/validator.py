import json
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL
from app.retrieval.retriever import retrieve
from app.models.schemas import Question

_client = Groq(api_key=GROQ_API_KEY)

PROMPT = """You are a strict question validator for educational assessments.
Verify that the correct answer is FULLY supported by the provided context.
Also verify that none of the wrong options are actually correct according to the context.

Question: {question_text}
Options: {options}
Declared correct answer: {correct_answer}

Context:
{context}

Return ONLY valid JSON:
{{
  "is_valid": true or false,
  "reason": "brief explanation"
}}"""


def validate_question(q: Question) -> tuple[bool, str]:
    """Returns (is_valid, reason)."""
    chunks = retrieve(q.concept)
    context = "\n\n".join(c["text"] for c in chunks)

    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT.format(
            question_text=q.question_text,
            options=q.options,
            correct_answer=q.correct_answer,
            context=context,
        )}],
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("is_valid", False), data.get("reason", "")