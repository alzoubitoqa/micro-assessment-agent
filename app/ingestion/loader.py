from pathlib import Path
from pypdf import PdfReader

def load_pdf(file_path: Path) -> list[dict]:
    reader = PdfReader(str(file_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({
                "file_name": file_path.name,
                "page_number": i + 1,
                "text": text,
            })
    return pages