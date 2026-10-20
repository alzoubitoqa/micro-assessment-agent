from pydantic import BaseModel

class Question(BaseModel):
    question_id: str
    concept: str
    difficulty: str
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: str
    source_chunk_ids: list[str]