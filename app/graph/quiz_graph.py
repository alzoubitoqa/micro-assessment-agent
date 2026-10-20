from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from app.agents.generator import generate_question
from app.agents.adaptive import generate_hint, simplify_question
from app.db.session_store import log_answer
from app.models.schemas import Question


class QuizState(TypedDict, total=False):
    session_id: str
    concept: str
    difficulty: str
    max_attempts: int

    question: Optional[dict]
    attempt: int
    student_answer: Optional[str]
    _last_wrong_answer: Optional[str]
    time_spent: float
    hint_text: Optional[str]

    is_correct: Optional[bool]
    done: bool
    feedback: str


def _serialize(q: Question) -> dict:
    return {
        "question_id": q.question_id,
        "concept": q.concept,
        "difficulty": q.difficulty,
        "question_text": q.question_text,
        "options": q.options,
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "source_chunk_ids": q.source_chunk_ids,
    }


def _deserialize(d: dict) -> Question:
    return Question(**d)


def _normalize(text: str) -> str:
    if text is None:
        return ""
    for a, w in zip("٠١٢٣٤٥٦٧٨٩", "0123456789"):
        text = text.replace(a, w)
    return text.strip().lower()


def _resolve(raw: str, options: list[str]) -> str:
    raw_norm = _normalize(raw)
    if raw_norm.isdigit():
        idx = int(raw_norm) - 1
        if 0 <= idx < len(options):
            return options[idx]
    return raw_norm


# ─── NODES ─────────────────────────────────────────────────────────

def generate_node(state: QuizState) -> dict:
    q = generate_question(state["concept"], state.get("difficulty", "medium"))
    if q is None:
        return {
            **state,
            "done": True,
            "feedback": "Failed to generate a valid question after multiple attempts.",
        }
    return {
        **state,
        "question": _serialize(q),
        "attempt": 1,
        "student_answer": None,
        "_last_wrong_answer": None,
        "hint_text": None,
        "is_correct": None,
        "done": False,
        "feedback": "",
    }


def evaluate_node(state: QuizState) -> dict:
    q = _deserialize(state["question"])
    answer = state["student_answer"]
    attempt = state["attempt"]
    max_attempts = state.get("max_attempts", 3)

    choice = _resolve(answer, q.options)
    is_correct = _normalize(choice) == _normalize(q.correct_answer)

    log_answer(
        session_id=state["session_id"],
        question=q,
        student_answer=answer,
        is_correct=is_correct,
        time_spent=state.get("time_spent", 0.0),
        hint_used=state.get("hint_text") is not None,
        hint_text=state.get("hint_text"),
        attempt_number=attempt,
        is_final_attempt=(is_correct or attempt >= max_attempts),
    )

    if is_correct:
        return {
            **state,
            "is_correct": True,
            "done": True,
            "student_answer": None,
            "feedback": f"Correct! {q.explanation}",
        }

    if attempt >= max_attempts:
        return {
            **state,
            "is_correct": False,
            "done": True,
            "student_answer": None,
            "feedback": (
                f"Wrong. Correct answer: {q.correct_answer}\n"
                f"Explanation: {q.explanation}\n"
                f"(Knowledge gap recorded)"
            ),
        }

    return {
        **state,
        "is_correct": False,
        "_last_wrong_answer": answer,
        "student_answer": None,
        "feedback": "Wrong answer.",
    }


def hint_node(state: QuizState) -> dict:
    q = _deserialize(state["question"])
    hint = generate_hint(q, state.get("_last_wrong_answer") or "")
    return {
        **state,
        "hint_text": hint,
        "attempt": state["attempt"] + 1,
    }


def simplify_node(state: QuizState) -> dict:
    q = _deserialize(state["question"])
    simplified = simplify_question(q)
    return {
        **state,
        "question": _serialize(simplified),
        "attempt": state["attempt"] + 1,
        "hint_text": None,
    }


# ─── ROUTING ───────────────────────────────────────────────────────

def route_entry(state: QuizState) -> Literal["generate", "evaluate", "end"]:
    if state.get("done"):
        return "end"
    if state.get("question") is None:
        return "generate"
    if state.get("student_answer") is not None:
        return "evaluate"
    return "end"


def route_after_evaluate(state: QuizState) -> Literal["hint", "simplify", "end"]:
    if state.get("done"):
        return "end"
    attempt = state.get("attempt", 1)
    if attempt == 1:
        return "hint"       # المحاولة 1 فشلت → تلميح (يرفع attempt إلى 2)
    if attempt == 2:
        return "simplify"   # المحاولة 2 فشلت → تبسيط (يرفع attempt إلى 3)
    return "end"            # المحاولة 3 هي الأخيرة (done=True من evaluate)


# ─── GRAPH BUILDER ─────────────────────────────────────────────────

def build_graph():
    g = StateGraph(QuizState)
    g.add_node("generate", generate_node)
    g.add_node("evaluate", evaluate_node)
    g.add_node("hint", hint_node)
    g.add_node("simplify", simplify_node)

    g.set_conditional_entry_point(route_entry, {
        "generate": "generate",
        "evaluate": "evaluate",
        "end": END,
    })

    g.add_edge("generate", END)

    g.add_conditional_edges("evaluate", route_after_evaluate, {
        "hint": "hint",
        "simplify": "simplify",
        "end": END,
    })

    g.add_edge("hint", END)
    g.add_edge("simplify", END)

    return g.compile()