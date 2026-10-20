from sentence_transformers import SentenceTransformer
from app.ingestion.embedder import collection, _model
from config import TOP_K_RETRIEVAL

def retrieve(query: str, top_k: int = TOP_K_RETRIEVAL) -> list[dict]:
    q_emb = _model.encode([query]).tolist()[0]
    res = collection.query(query_embeddings=[q_emb], n_results=top_k)
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "chunk_id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out