import os
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict

DEFAULT_SPACY_MODEL = os.getenv("DEFAULT_SPACY_MODEL", "pt_core_news_sm")
NLP_WORKERS = int(os.getenv("NLP_WORKERS", "2"))

_nlp = None

def _preprocess_sync(text: str, top_n: int = 15) -> Dict:
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    
    try:
        import string
        
        text_clean = text.translate(str.maketrans('', '', string.punctuation)).lower()
        
        tokens = text_clean.split()
        
        stopwords = {'e', 'o', 'a', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'não', 'na', 'no', 'que', 'se', 'por', 'mais', 'as', 'os', 'é', 'são', 'foi', 'foram'}
        filtered_tokens = [token for token in tokens if token not in stopwords and len(token) > 2]
        
        from collections import Counter
        token_counts = Counter(filtered_tokens)
        
        cleaned_text = ' '.join(filtered_tokens)
        
        top_tokens = [{"token": token, "count": count} for token, count in token_counts.most_common(top_n)]
        
        return {
            "cleaned_text": cleaned_text,
            "tokens": filtered_tokens,
            "unique_tokens": len(set(filtered_tokens)),
            "total_tokens": len(filtered_tokens),
            "top_tokens": top_tokens,
            "original_len": len(text),
        }
    except Exception as exc:
        raise RuntimeError(f"NLP preprocessing failed: {exc}") from exc

def preprocess_sync(text: str, top_n: int = 15) -> Dict:
    return _preprocess_sync(text, top_n=top_n)

_process_executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=NLP_WORKERS)

async def preprocess_async(text: str, top_n: int = 15) -> Dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_process_executor, _preprocess_sync, text, top_n)
