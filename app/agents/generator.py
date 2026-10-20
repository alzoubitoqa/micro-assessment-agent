import json, hashlib, re
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALIDATE_QUESTIONS
from app.retrieval.retriever import retrieve
from app.models.schemas import Question

_client = Groq(api_key=GROQ_API_KEY)

PROMPT = """You are a university-level formative assessment question generator.
Use ONLY the information in the context below. Do not add any external knowledge.
If the context is insufficient, return {{"error": "insufficient_context"}}.

The lecture is in English. The question, options, and explanation MUST be written in English.

Context:
{context}

Concept: {concept}
Difficulty level: {difficulty}

Return ONLY valid JSON in this exact schema, with EXACTLY 4 options (no more, no less):
{{
  "question_text": "...",
  "options": ["...", "...", "...", "..."],
  "correct_answer": "...",
  "explanation": "...",
  "source_chunk_ids": ["chunk_id_1", "chunk_id_2"]
}}"""


def _clean_chunk_id(cid: str) -> str:
    return re.sub(r"[\[\]]", "", cid).strip()


def _generate_once(concept: str, difficulty: str) -> Question | None:
    chunks = retrieve(concept)
    if not chunks:
        return None

    context = "\n\n".join(f"<<{c['chunk_id']}>>\n{c['text']}" for c in chunks)

    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT.format(
            context=context, concept=concept, difficulty=difficulty,
        )}],
    )
    data = json.loads(resp.choices[0].message.content)
    if "error" in data:
        return None

    options = [o.strip() for o in data.get("options", []) if o and o.strip()]
    if len(options) != 4:
        return None
    if data.get("correct_answer") not in options:
        return None

    chunk_ids = [_clean_chunk_id(c) for c in data.get("source_chunk_ids", [])]
    chunk_ids = [c for c in chunk_ids if c]

    h = hashlib.md5((context + concept + difficulty).encode()).hexdigest()[:6]
    return Question(
        question_id=f"q_{concept.replace(' ', '_')}_{difficulty}_{h}",
        concept=concept,
        difficulty=difficulty,
        question_text=data["question_text"],
        options=options,
        correct_answer=data["correct_answer"],
        explanation=data["explanation"],
        source_chunk_ids=chunk_ids,
    )


def generate_question(concept: str, difficulty: str = "medium",
                      max_retries: int = 2) -> Question | None:
    for attempt in range(max_retries):
        q = _generate_once(concept, difficulty)
        if q is None:
            continue

        if not VALIDATE_QUESTIONS:
            return q

        from app.agents.validator import validate_question
        is_valid, reason = validate_question(q)
        if is_valid:
            print(f"   ✓ Validated (attempt {attempt + 1})")
            return q
        print(f"   ✗ Validation failed: {reason[:80]}...")

    return None