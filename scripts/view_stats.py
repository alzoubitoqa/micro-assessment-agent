from app.db.session_store import init_db, get_concept_heatmap, list_recent_sessions


def main():
    init_db()

    print("=== Recent Sessions ===")
    sessions = list_recent_sessions(5)
    if not sessions:
        print("  (no sessions yet)")
    for s in sessions:
        print(f"  {s['session_id']} | {s['student_id']} | "
              f"{s['correct_count']}/{s['total_questions']} | {s['started_at'][:16]}")

    print("\n=== Heatmap: failure rate per concept ===")
    heatmap = get_concept_heatmap()
    if not heatmap:
        print("  (no answers recorded yet)")
        return

    for row in heatmap:
        bar = "#" * int(row["failure_rate"] * 20)
        color = "RED" if row["failure_rate"] > 0.6 else ("YEL" if row["failure_rate"] > 0.3 else "GRN")
        print(f"  [{color}] {row['concept']:<30} "
              f"failure {row['failure_rate']*100:5.1f}%  {bar}")


if __name__ == "__main__":
    main()