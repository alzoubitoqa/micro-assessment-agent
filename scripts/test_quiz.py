import random
import time
from app.agents.concept_extractor import extract_concepts, list_available_lectures
from app.db.session_store import (
    init_db, create_session, end_session, get_session_stats,
)
from app.graph.quiz_graph import build_graph


def choose_lecture_and_concept() -> tuple[str, str]:
    lectures = list_available_lectures()
    if not lectures:
        print("No lectures found. Run: python -m scripts.ingest_lectures")
        return "", ""

    print("\n=== Available Lectures ===")
    for i, lec in enumerate(lectures, 1):
        print(f"  {i}) {lec}")

    lec_choice = input("\nChoose lecture number: ").strip()
    if not lec_choice.isdigit() or not (1 <= int(lec_choice) <= len(lectures)):
        print("Invalid choice.")
        return "", ""
    file_name = lectures[int(lec_choice) - 1]

    print(f"\nExtracting concepts from: {file_name}\n")
    concepts = extract_concepts(file_name)
    if not concepts:
        print("No concepts extracted.")
        return "", ""

    print("=== Extracted Concepts ===")
    for i, c in enumerate(concepts, 1):
        pages = ", ".join(str(p) for p in c.get("source_pages", []))
        print(f"  {i}) {c['name']}  [{c.get('difficulty', '?')}]  (pages: {pages})")

    print("\n  0) Random question")
    choice = input("\nChoose concept number: ").strip()
    if not choice.isdigit() or not (0 <= int(choice) <= len(concepts)):
        print("Invalid choice.")
        return "", ""
    if int(choice) == 0:
        return file_name, random.choice(concepts)["name"]
    return file_name, concepts[int(choice) - 1]["name"]


def run_question(session_id: str, concept: str,
                 difficulty: str = "medium",
                 max_attempts: int = 3) -> bool:
    graph = build_graph()
    state: dict = {
        "session_id": session_id,
        "concept": concept,
        "difficulty": difficulty,
        "max_attempts": max_attempts,
        "question": None,
        "attempt": 0,
        "student_answer": None,
        "time_spent": 0.0,
        "hint_text": None,
        "is_correct": None,
        "done": False,
        "feedback": "",
    }

    # First invocation: generates question
    state = graph.invoke(state)

    while not state.get("done"):
        if state.get("question") is None:
            print(f"\n{state.get('feedback', 'Failed to generate question.')}")
            return False

        q = state["question"]
        attempt = state["attempt"]
        print(f"\n--- Attempt {attempt}/{max_attempts} ---")
        print(f"[sources: {q['source_chunk_ids']}]")

        if state.get("hint_text"):
            print(f"\nHint: {state['hint_text']}")

        print(f"\nQ: {q['question_text']}\n")
        for i, opt in enumerate(q["options"], 1):
            print(f"  {i}) {opt}")

        t0 = time.time()
        raw = input("\nYour answer (number or text): ").strip()
        elapsed = time.time() - t0

        state["student_answer"] = raw
        state["time_spent"] = elapsed
        state = graph.invoke(state)

        # Print feedback only if the graph is NOT done
        # (when done=True, we print it once after the loop)
        fb = state.get("feedback", "")
        if fb and not state.get("done"):
            print(f"\n{fb}")

    # Print the final feedback once (correct, wrong, or failed)
    final_fb = state.get("feedback", "")
    if final_fb:
        print(f"\n{final_fb}")

    return state.get("is_correct", False)


def main():
    init_db()
    lecture_file, concept = choose_lecture_and_concept()
    if not concept:
        return

    student_id = input("\nYour name (student_id): ").strip() or "student_demo"
    session_id = create_session(student_id, lecture_file)
    print(f"Session created: {session_id}\n")

    print(f"Running adaptive quiz for: {concept}\n")
    run_question(session_id, concept)

    end_session(session_id)
    stats = get_session_stats(session_id)
    print(f"\nSession result: {stats['correct_count']}/{stats['total_questions']} correct")
    print("   (saved to data/sessions.db)")


if __name__ == "__main__":
    main()