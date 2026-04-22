import re
from pathlib import Path
from uuid import uuid4

import fitz

from backend.config import get_settings


settings = get_settings()


def extract_pdf_text(file_bytes: bytes) -> str:
    document = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [page.get_text("text") for page in document]
    document.close()
    return "\n".join(pages)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_bytes(filename: str, file_bytes: bytes) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(file_bytes)
        file_type = "pdf"
    elif extension in {".txt", ".md", ".text"}:
        text = file_bytes.decode("utf-8", errors="ignore")
        file_type = "text"
    else:
        raise ValueError("Unsupported file type. Please upload a PDF or text file.")

    cleaned = clean_text(text)
    if not cleaned:
        raise ValueError("The uploaded project does not contain extractable text.")

    return cleaned, file_type


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[dict]:
    words = text.split()
    if not words:
        return []

    chunks: list[dict] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if not chunk_words:
            continue
        chunks.append(
            {
                "chunk_id": len(chunks),
                "text": " ".join(chunk_words),
                "start_word": start,
                "end_word": end,
            }
        )
        if end >= len(words):
            break
    return chunks


def save_uploaded_file(filename: str, file_bytes: bytes) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    destination = settings.upload_dir / f"{uuid4().hex}_{safe_name}"
    destination.write_bytes(file_bytes)
    return str(destination)

