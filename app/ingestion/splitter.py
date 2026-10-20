from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", "، ", " ", ""],
)

def split_pages(pages: list[dict]) -> list[dict]:
    chunks = []
    for page in pages:
        for j, text in enumerate(_splitter.split_text(page["text"])):
            chunks.append({
                "file_name": page["file_name"],
                "page_number": page["page_number"],
                "chunk_id": f"{page['file_name']}_p{page['page_number']}_c{j}",
                "text": text,
            })
    return chunks