from app.ingestion.loader import load_pdf
from app.ingestion.splitter import split_pages
from app.ingestion.embedder import embed_and_store
from config import LECTURES_DIR

def main():
    pdfs = list(LECTURES_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"لا توجد PDFs في {LECTURES_DIR}")
        return

    all_chunks = []
    for pdf in pdfs:
        print(f"→ {pdf.name}")
        pages = load_pdf(pdf)
        chunks = split_pages(pages)
        all_chunks.extend(chunks)
        print(f"   {len(pages)} صفحات، {len(chunks)} قطع")

    print(f"\nتضمين {len(all_chunks)} قطعة...")
    embed_and_store(all_chunks)
    print("✓ Vector store جاهز في data/chroma_db/")

if __name__ == "__main__":
    main()