import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_DIR, EMBEDDING_MODEL

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = _client.get_or_create_collection("lectures")
_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_and_store(chunks: list[dict], batch_size: int = 100) -> None:
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadatas = [{k: v for k, v in c.items() if k != "text"} for c in batch]
        embeddings = _model.encode(texts, show_progress_bar=False).tolist()
        
        # التعديل هنا: استخدام upsert بدلاً من add
        collection.upsert(
            ids=ids, 
            embeddings=embeddings, 
            documents=texts, 
            metadatas=metadatas
        )