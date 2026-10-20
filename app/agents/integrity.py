from app.db.session_store import _conn

class IntegrityAgent:
    def __init__(self, min_seconds: float = 3.0, min_flags: int = 1):
        self.min_seconds = min_seconds
        self.min_flags = min_flags

    def analyze(self) -> list[dict]:
        """
        يحلل الإجابات الصحيحة من المحاولة الأولى التي تمت في زمن أقل من الحد المسموح.
        """
        query = """
            SELECT s.session_id, s.student_id, s.lecture_file, a.concept, a.time_spent_seconds
            FROM answers a
            JOIN sessions s ON a.session_id = s.session_id
            WHERE a.is_correct = 1 AND a.attempt_number = 1 AND a.time_spent_seconds < ?
            ORDER BY s.started_at DESC
        """
        with _conn() as conn:
            rows = conn.execute(query, (self.min_seconds,)).fetchall()

        # تجميع النتائج حسب الجلسة
        sessions = {}
        for r in rows:
            sid = r["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid, 
                    "student_id": r["student_id"], 
                    "lecture_file": r["lecture_file"],
                    "flags": []
                }
            sessions[sid]["flags"].append({
                "concept": r["concept"],
                "time": round(r["time_spent_seconds"], 2)
            })

        # فلترة الجلسات التي تجاوزت الحد الأدنى من الإنذارات
        results = []
        for sid, data in sessions.items():
            if len(data["flags"]) >= self.min_flags:
                results.append({
                    "Session ID": sid,
                    "Student": data["student_id"],
                    "Lecture": data["lecture_file"],
                    "Suspicious Answers": len(data["flags"]),
                    "Details (Concept & Time)": ", ".join([f"{f['concept']} ({f['time']}s)" for f in data["flags"]])
                })
        return results