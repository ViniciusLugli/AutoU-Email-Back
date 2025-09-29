import os
import pdfplumber
import asyncio

def read_file_sync(path: str, encoding: str = "utf-8") -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    if path.lower().endswith(".pdf"):
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    else:
        with open(path, "r", encoding=encoding) as f:
            return f.read()

async def read_file_async(path: str, encoding: str = "utf-8") -> str:
    return await asyncio.to_thread(read_file_sync, path, encoding)
