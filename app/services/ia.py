import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
import google.genai as genai
from datetime import datetime
from app.models import Category

GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gemma-3-1b-it")

if GENAI_API_KEY:
    try:
        if hasattr(genai, "configure"):
            genai.configure(api_key=GENAI_API_KEY)
        else:
            os.environ.setdefault("GOOGLE_API_KEY", GENAI_API_KEY)
    except Exception:
        pass


def _call_genai_blocking(prompt: str) -> str:
    if not GENAI_API_KEY:
        raise RuntimeError("GenAI API not configured: set GENAI_API_KEY")
    if not hasattr(genai, "Client"):
        raise RuntimeError("google.genai client (genai.Client) is not available in this environment")

    try:
        try:
            from google.genai import types as genai_types
        except Exception:
            genai_types = None
        client = genai.Client(api_key=GENAI_API_KEY)

        if genai_types is not None:
            contents = [
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=prompt)],
                )
            ]
            max_tokens = int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", "2056"))
            temperature = float(os.getenv("GENAI_TEMPERATURE", "0.0"))
            config = genai_types.GenerateContentConfig(max_output_tokens=max_tokens, temperature=temperature)

            if hasattr(client.models, "generate_content_stream"):
                response_text = ""
                for chunk in client.models.generate_content_stream(model=GENAI_MODEL, contents=contents, config=config):
                    chunk_text = (
                        getattr(chunk, "text", None)
                        or getattr(chunk, "delta", None)
                        or getattr(chunk, "content", None)
                        or str(chunk)
                    )
                    response_text += str(chunk_text)
            else:
                resp = client.models.generate_content(model=GENAI_MODEL, contents=contents, config=config)
                response_text = getattr(resp, "text", str(resp))
        else:
            max_tokens = int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", "2056"))
            temperature = float(os.getenv("GENAI_TEMPERATURE", "0.0"))
            resp = client.models.generate_content(
                model=GENAI_MODEL,
                contents=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                max_output_tokens=max_tokens if hasattr(client.models, "generate_content") else None,
                temperature=temperature if hasattr(client.models, "generate_content") else None,
            )
            response_text = getattr(resp, "text", str(resp))
    except Exception as exc:
        raise RuntimeError(f"genai.Client call failed: {exc}") from exc


    return response_text


def _clean_sdk_artifacts(s: str) -> str:
    if not s:
        return s
    import re

    out = s

    metadata_tokens = [
        "sdk_http_response",
        "candidates",
        "usage_metadata",
        "parsed",
        "create_time",
        "model_version",
        "prompt_feedback",
        "response_id",
        "candidates_token_count",
        "prompt_token_count",
        "total_token_count",
        "automatic_function_calling_history",
    ]
    lowest_idx = None
    for tk in metadata_tokens:
        idx = out.find(tk)
        if idx != -1:
            if lowest_idx is None or idx < lowest_idx:
                lowest_idx = idx
    if lowest_idx is not None:
        out = out[:lowest_idx]

    out = re.sub(r"sdk_http_response=HttpResponse\([^\)]*\)", "", out)
    out = re.sub(r"candidates=\[.*?\]\s*", "", out, flags=re.DOTALL)
    out = re.sub(r"usage_metadata=[^\n]*", "", out)
    out = re.sub(r"parsed=[^,\n]*", "", out)

    out = re.sub(r"\n{3,}", "\n\n", out)

    return out



def build_prompt(text: str, username: str | None = None) -> str:
    examples = [
        {
            "email": "Prezada equipe,\n\nFinalizei o relatório mensal e já o subi na pasta \\Relatórios_2025\\.\nA reunião de alinhamento será terça-feira às 10h.\r\nPor favor, revisem antes.\n\nAtenciosamente,\nCarlos",
            "category": "PRODUTIVO",
            "reason": "O email contém informações de trabalho claras: entrega de relatório e marcação de reunião.",
            "suggested_response": "Obrigado, Carlos! Vamos revisar o relatório antes da reunião.\nAté terça-feira."
        },
        {
            "email": "Oi pessoal,\n\nVocês viram aquele vídeo engraçado que mandei no grupo? kkkkk\nE aí, sexta vai ter happy hour ou não?\n\nAbraços,\nJoão",
            "category": "IMPRODUTIVO",
            "reason": "O email trata apenas de assuntos pessoais e piadas, sem relação com trabalho.",
            "suggested_response": "Oi João, vamos focar os emails apenas em questões do trabalho.\nSobre o happy hour, podemos falar no grupo do WhatsApp. :)"
        },
        {
            "email": "Bom dia,\n\nEnviei a planilha de custos atualizada.\r\nEstá em: C:\\Projetos\\Financeiro\\2025\\.\nVerifiquem antes da reunião de orçamento.\n\nAbs,\nFernanda",
            "category": "PRODUTIVO",
            "reason": "Email contém envio de documento importante e solicitação de revisão.",
            "suggested_response": "Obrigado, Fernanda! Já recebemos a planilha.\nVamos revisar antes da reunião."
        },
        {
            "email": "Oi,\n\nEstava pensando... vocês acham que a nova temporada da série X ficou boa?\nPodemos conversar no café mais tarde!\n\nBeijos,\nLuiza",
            "category": "IMPRODUTIVO",
            "reason": "O conteúdo não tem relação com atividades de trabalho, apenas lazer.",
            "suggested_response": "Oi Luiza! Vamos manter os emails apenas para trabalho.\nPodemos falar da série no café sim. :)"
        },
        {
            "email": "Equipe,\n\nPrecisamos enviar o material para o cliente até amanhã às 17h.\nJá organizei os arquivos no Google Drive: https://drive.google.com/projeto2025.\n\n[]s,\nRafael",
            "category": "PRODUTIVO",
            "reason": "O email define prazo e organiza entrega de material para cliente.",
            "suggested_response": "Obrigado, Rafael!\nVamos garantir que tudo esteja pronto e validado até amanhã às 17h."
        },
        {
            "email": "Gente,\n\nOlhem esse meme:\nhttps://imgur.com/123abc 😂😂😂\n\nkkkkkk\n\nAbraços,\nPedro",
            "category": "IMPRODUTIVO",
            "reason": "Conteúdo de humor sem valor profissional, apenas distração.",
            "suggested_response": "Oi Pedro, vamos deixar memes para grupos informais.\nAqui no email precisamos focar em demandas de trabalho."
        },
        {
            "email": "Prezados,\n\nO cronograma atualizado do projeto Alfa já está disponível.\nLocal: /mnt/projetos/alfa/cronograma.xlsx\n\nPeço que confirmem se todos os prazos estão corretos.\n\nObrigado,\nMariana",
            "category": "PRODUTIVO",
            "reason": "Atualização de cronograma é informação relevante e necessária para andamento do projeto.",
            "suggested_response": "Obrigado, Mariana!\nVamos revisar os prazos e dar retorno ainda hoje."
        },
        {
            "email": "Fala galera,\n\nVamos pedir pizza hoje no almoço?\nQual sabor vcs querem? 🍕\n\nAbs,\nThiago",
            "category": "IMPRODUTIVO",
            "reason": "Email informal sobre almoço, não relacionado ao trabalho.",
            "suggested_response": "Oi Thiago, bora combinar isso pessoalmente.\nNo email, vamos focar nas demandas do projeto. :)"
        },
        {
            "email": "Boa tarde,\n\nAnexei o documento com os indicadores de desempenho (KPI) do último trimestre.\nEle está em PDF, nome: Indicadores_Q3.pdf\n\nAtenciosamente,\nBeatriz",
            "category": "PRODUTIVO",
            "reason": "O email fornece dados de desempenho que fazem parte do acompanhamento do trabalho.",
            "suggested_response": "Obrigado, Beatriz!\nDocumento recebido.\nVamos analisar os indicadores e discutir na próxima reunião."
        },
        {
            "email": "Oi,\n\nAlguém sabe se sexta é feriado mesmo? Não quero vir à toa kkkkk\n\nValeu,\nAndré",
            "category": "IMPRODUTIVO",
            "reason": "Pergunta informal que poderia ser resolvida em calendário oficial ou grupo informal.",
            "suggested_response": "Oi André, confira no calendário oficial da empresa para confirmar.\nAssim garantimos que todos estejam alinhados."
        }
    ]

    username_line = f"Usuário: {username}\n" if username else ""

    instructions = (
        "INSTRUÇÕES (OBRIGATÓRIO): Você é um assistente que analisa e classifica e-mails em duas categorias: PRODUTIVO ou IMPRODUTIVO.\n"
        "- PRODUTIVO: e-mails que requerem ação ou resposta específica.\n"
        "- IMPRODUTIVO: e-mails que não necessitam de ação imediata (piadas, convites sociais, mensagens sem relação direta ao trabalho).\n\n"
        "SAÍDA OBRIGATÓRIA:\n"
        "1) PRIMEIRA LINHA: apenas a CATEGORIA em maiúsculas: PRODUTIVO ou IMPRODUTIVO.\n"
        "2) SEGUNDA LINHA: 'CONFIDENCE: <valor>' entre 0 e 1.\n"
        "3) TERCEIRA LINHA EM DIANTE: 'RESPOSTA_SUGERIDA:' seguido do texto da resposta.\n\n"
        "REGRAS PARA RESPOSTA_SUGERIDA:\n"
        "- É PROIBIDO repetir ou reescrever o conteúdo do e-mail recebido.\n"
        "- Escreva como se fosse um colega respondendo ao remetente.\n"
        "- A resposta deve ser curta, clara e acrescentar valor (ex.: agradecer, confirmar recebimento, indicar próxima ação).\n"
        "- Use tom educado e profissional.\n"
        "- Preserve formatação: quebras de linha (\\n, \\r), barras (\\\\), acentuação e caracteres especiais.\n\n"
        "Exemplo negativo (NÃO FAZER):\n"
        "Texto original: 'Finalizei o relatório e marquei reunião.'\n"
        "Resposta incorreta: 'Você finalizou o relatório e marcou reunião.' (apenas reescreve o email)\n\n"
        "Exemplo positivo (CORRETO):\n"
        "Texto original: 'Finalizei o relatório e marquei reunião.'\n"
        "Resposta correta: 'Obrigado pelo envio do relatório. Vou revisar e estarei presente na reunião.'\n"
        "- Utilize os exemplos abaixo para entender o estilo e formatação da resposta desejados.\n"
    )


    ex_texts: list[str] = []
    for ex in examples:
        ex_lines = [
            f"EMAIL: {ex.get('email','')}",
            f"CATEGORIA: {ex.get('category','')}",
            f"RAZAO: {ex.get('reason','')}",
            f"RESPOSTA_SUGERIDA: {ex.get('suggested_response','')}",
        ]
        ex_texts.append("\n".join(ex_lines))

    prompt_parts = [instructions, "\n\n".join(ex_texts), "\nANALISE O SEGUINTE EMAIL A PARTIR DAQUI:", username_line, "\nTEXTO:\n", text]

    prompt = "\n\n".join([p for p in prompt_parts if p])
    return prompt


_INFER_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("IA_ASYNC_WORKERS", "1")))


async def infer_async(text: str, username: str | None = None) -> Dict[str, Any]:
    prompt = build_prompt(text, username)
    try:
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(_INFER_EXECUTOR, _call_genai_blocking, prompt)
    except Exception as exc:
        raise RuntimeError(f"GenAI async infer failed: {exc}") from exc

    cleaned = _clean_sdk_artifacts(response_text)

    category = Category.SEM_CLASSIFICACAO
    confidence = None
    parsed_generated = ""

    if cleaned:
        lines = [l for l in cleaned.splitlines()]
        if len(lines) >= 1:
            import re as _re
            first_raw = lines[0].strip()
            m = _re.search(r"(?:CATEGORIA\s*:\s*)?(PRODUTIVO|IMPRODUTIVO)", first_raw, flags=_re.IGNORECASE)
            if m:
                tok = m.group(1).strip().upper()
                if tok == "PRODUTIVO":
                    category = Category.PRODUTIVO
                elif tok == "IMPRODUTIVO":
                    category = Category.IMPRODUTIVO
        if len(lines) >= 2:
            second = lines[1].strip()
            if second.upper().startswith("CONFIDENCE:"):
                try:
                    val = second.split(":", 1)[1].strip()
                    if val.lower() != "null":
                        confidence = float(val)
                except Exception:
                    confidence = None
            parsed_generated = "\n".join(lines[2:]).strip()
            if parsed_generated.upper().startswith("RESPOSTA_SUGERIDA:"):
                parsed_generated = parsed_generated[len("RESPOSTA_SUGERIDA:"):].strip()

        else:
            parsed_generated = cleaned

    if not parsed_generated:
        try:
            import re as _re

            cleaned_rest = _re.sub(r"^\s*(PRODUTIVO|IMPRODUTIVO)\s*(?:\n|\s)*?(?:CONFIDENCE\s*:\s*[0-9\.]+)?\s*[:\-\n\s]*", "", cleaned, flags=_re.IGNORECASE)
            cleaned_rest = _re.sub(r"RESPOSTA_SUGERIDA\s*:\s*", "", cleaned_rest, flags=_re.IGNORECASE)
            parsed_generated = cleaned_rest.strip()
        except Exception:
            parsed_generated = parsed_generated

    def _strip_prefix_case_insensitive(s: str, prefix: str) -> str:
        if not s:
            return s
        if s.upper().startswith(prefix.upper()):
            return s[len(prefix):].strip()
        return s

    final_generated = (parsed_generated or "").strip()
    final_generated = _strip_prefix_case_insensitive(final_generated, "RESPOSTA_SUGERIDA:")

    return {
        "category": category.value if isinstance(category, Category) else (str(category) if category is not None else None),
        "confidence": confidence,
        "generated_response": final_generated,
    }

