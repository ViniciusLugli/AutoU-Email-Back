from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import threading
import time
import re

app = FastAPI()

@app.post("/")
async def root(req: Request):
    body = await req.json()
    task = body.get("task")
    text = body.get("text", "")
    mode = req.query_params.get("mode") or body.get("mode") or "produtivo"

    if task == "nlp":
        tokens = [re.sub(r"[^a-zA-ZÀ-ÿ0-9#]", "", t).lower() for t in text.split()]
        tokens = [t for t in tokens if t]
        cleaned_text = " ".join(tokens)
        counts = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        top_tokens = sorted(list(counts.items()), key=lambda x: (-x[1], x[0]))
        return JSONResponse({
            "cleaned_text": cleaned_text,
            "tokens": tokens,
            "unique_tokens": len(counts),
            "total_tokens": len(tokens),
            "top_tokens": top_tokens,
            "original_len": len(text),
        })

    if task == "infer":
        # generate a response that references the content
        if mode == "improdutivo":
            category = "Improdutivo"
            confidence = 0.2
            generated = f"Recebemos sua mensagem: '{text[:120]}'. No momento não é possível realizar ação automática."
        else:
            category = "Produtivo"
            confidence = 0.95
            # attempt to pull a reference like an order number
            match = re.search(r"#\d+", text)
            if match:
                ref = match.group(0)
                generated = f"Posso atualizar o pedido {ref} e confirmar os próximos passos. Você confirma?"
            else:
                generated = f"Posso ajudar com sua solicitação: '{text[:120]}'. Quais próximos passos prefere?"
        return JSONResponse({
            "category": category,
            "confidence": confidence,
            "generated_response": generated
        })

    return JSONResponse({"error": "unknown task"}, status_code=400)


def start_mock(port: int = 9001, mode: str = "produtivo"):
    def run():
        uvicorn.run(app, host="127.0.0.1", port=port)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.5)
    return t
