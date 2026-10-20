import json
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, DATA_DIR
from app.ingestion.embedder import collection

_client = Groq(api_key=GROQ_API_KEY)
CONCEPTS_CACHE = DATA_DIR / "concepts_cache.json"

PROMPT = """You are an educational content analyzer. Analyze the following lecture content and extract the key concepts that a university student should be assessed on.

For each concept, provide:
- "name": a concise English term (2-4 words) exactly as written in the lecture
- "description": one-sentence explanation of what it covers
- "difficulty": "easy", "medium", or "hard"
- "source_pages": list of page numbers where it appears

Focus on 5-10 core concepts that represent the most important learning outcomes.
Return ONLY valid JSON: {{"concepts": [...]}}

Lecture content (from file: {file_name}):
{content}"""


def _get_chunks_for_file(file_name: str) -> list[dict]:
    results = collection.get(where={"file_name": file_name})
    chunks = []
    for i in range(len(results["ids"])):
        chunks.append({
            "chunk_id": results["ids"][i],
            "text": results["documents"][i],
            "page": results["metadatas"][i].get("page_number", 0),
        })
    chunks.sort(key=lambda c: (c["page"], c["chunk_id"]))
    return chunks


def extract_concepts(file_name: str, force_refresh: bool = False) -> list[dict]:
    if not force_refresh and CONCEPTS_CACHE.exists():
        cache = json.loads(CONCEPTS_CACHE.read_text(encoding="utf-8"))
        if file_name in cache:
            return cache[file_name]

    chunks = _get_chunks_for_file(file_name)
    if not chunks:
        return []

    content = "\n\n".join(f"[Page {c['page']}] {c['text']}" for c in chunks)
    if len(content) > 20000:
        content = content[:20000]

    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT.format(
            file_name=file_name, content=content,
        )}],
    )
    data = json.loads(resp.choices[0].message.content)
    concepts = data.get("concepts", [])

    cache = {}
    if CONCEPTS_CACHE.exists():
        cache = json.loads(CONCEPTS_CACHE.read_text(encoding="utf-8"))
    cache[file_name] = concepts
    CONCEPTS_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return concepts


def list_available_lectures() -> list[str]:
    results = collection.get()
    files = {m["file_name"] for m in results["metadatas"] if "file_name" in m}
    return sorted(files)