import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import google.genai as genai
from app.models import Category
from app.core.constants import GENAI_API_KEY, GENAI_MAX_OUTPUT_TOKENS, GENAI_MODEL, GENAI_TEMPERATURE, IA_ASYNC_WORKERS

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
            config = genai_types.GenerateContentConfig(max_output_tokens=GENAI_MAX_OUTPUT_TOKENS, temperature=GENAI_TEMPERATURE)

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
            resp = client.models.generate_content(
                model=GENAI_MODEL,
                contents=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                max_output_tokens=GENAI_MAX_OUTPUT_TOKENS if hasattr(client.models, "generate_content") else None,
                temperature=GENAI_TEMPERATURE if hasattr(client.models, "generate_content") else None,
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
            "email": "Prezada equipe,\n\nFinalizei o relatório trimestral de desempenho e já o disponibilizei na pasta compartilhada: \\\\Servidor\\Projetos\\Relatorios\\2025_Q1\\.\nAlém do relatório em PDF, incluí também uma planilha em Excel com os indicadores detalhados por área (financeiro, comercial e operacional).\r\n\r\nMarquei a reunião de revisão para quarta-feira, dia 15/10, às 14h, via Microsoft Teams. O link já está no calendário, mas segue aqui também: https://teams.microsoft.com/l/meetup-join/123.\n\nPeço que todos leiam os tópicos 3.2 e 4.1 do relatório antes da reunião, pois serão foco de discussão.\n\nAtenciosamente,\nCarlos",
            "category": "PRODUTIVO",
            "reason": "O email contém entrega de relatórios, anexos em formatos diferentes, local de armazenamento, link de reunião e instruções claras para preparação.",
            "suggested_response": "Olá Carlos,\n\nObrigado pelo envio do relatório trimestral e da planilha detalhada. Já acessamos os arquivos na pasta compartilhada (\\\\Servidor\\Projetos\\Relatorios\\2025_Q1\\).\n\nVamos revisar especialmente os tópicos 3.2 e 4.1 antes da reunião de quarta-feira (15/10 às 14h).\n\nAté lá,\nEquipe"
        },
        {
            "email": "Bom dia,\n\nEnviei a versão final do contrato com o cliente XYZ. O documento foi salvo em: C:\\Users\\Public\\Documentos\\Contratos\\XYZ_Final.pdf\n\nSolicito que a equipe jurídica faça a revisão até amanhã, 29/09, para que possamos enviar ao cliente ainda dentro do prazo.\r\n\r\nAlém disso, precisamos que o time de finanças valide os valores da cláusula 5.3 (ajustes de pagamento).\n\nAbraços,\nFernanda",
            "category": "PRODUTIVO",
            "reason": "O email trata de contrato, prazos de revisão e validação de cláusulas financeiras.",
            "suggested_response": "Bom dia Fernanda,\n\nRecebemos o contrato salvo em C:\\Users\\Public\\Documentos\\Contratos\\XYZ_Final.pdf.\n\nA equipe jurídica vai revisar os pontos legais até amanhã (29/09) e o financeiro validará os valores da cláusula 5.3.\n\nTe daremos retorno antes do prazo.\n\nAbs,\nEquipe"
        },
        {
            "email": "Prezados,\n\nO cronograma atualizado do projeto Ômega já está disponível em: /mnt/projetos/omega/cronograma_v2.xlsx\n\nAs principais mudanças:\n- Entrega do módulo de autenticação adiada para 20/10.\n- Inclusão de uma nova etapa de testes de integração entre 22/10 e 25/10.\r\n- Ajustes nas dependências do módulo de relatórios.\n\nPor favor, confirmem se todos os responsáveis estão de acordo com as novas datas.\n\nObrigado,\nMariana",
            "category": "PRODUTIVO",
            "reason": "O email comunica mudanças relevantes no cronograma e pede validação da equipe.",
            "suggested_response": "Oi Mariana,\n\nObrigado pelo envio do cronograma atualizado em /mnt/projetos/omega/cronograma_v2.xlsx.\n\nJá verificamos as mudanças: entrega do módulo de autenticação (20/10), etapa de testes de integração (22/10-25/10) e ajustes no módulo de relatórios.\n\nNossa equipe confirma que está de acordo com as novas datas.\n\nAtenciosamente,\nEquipe"
        },
        {
            "email": "Boa tarde,\n\nAnexei o documento Indicadores_Q2.pdf com os resultados de desempenho do segundo trimestre.\nPrincipais pontos a observar:\r\n1) Crescimento de 12% no setor comercial.\n2) Redução de custos operacionais em 8%.\n3) Atraso na entrega de dois projetos (detalhes no anexo).\n\nSolicito que cada gestor prepare comentários sobre os indicadores de sua área para a reunião de sexta-feira, às 11h.\n\nAbraços,\nBeatriz",
            "category": "PRODUTIVO",
            "reason": "O email contém indicadores de desempenho e solicita análise da equipe antes da reunião.",
            "suggested_response": "Boa tarde Beatriz,\n\nObrigado pelo envio do documento Indicadores_Q2.pdf.\n\nJá notamos os principais pontos: crescimento comercial (12%), redução de custos operacionais (8%) e atrasos em dois projetos.\n\nCada gestor vai preparar os comentários de sua área antes da reunião de sexta-feira às 11h.\n\nAbs,\nEquipe"
        },
        {
            "email": "Equipe,\n\nLembrando que o material para a apresentação do cliente XPTO deve ser finalizado até quinta-feira (02/10), às 18h.\nO conteúdo parcial está salvo no Google Drive: https://drive.google.com/projetoXPTO.\r\n\r\nAinda faltam os slides de resultados financeiros e o gráfico de tendências.\n\nPeço que cada responsável atualize sua parte até quarta-feira, para termos um dia de folga para revisão final.\n\n[]s,\nRafael",
            "category": "PRODUTIVO",
            "reason": "O email define prazos claros, aponta pendências e reforça a importância da entrega antecipada para revisão.",
            "suggested_response": "Oi Rafael,\n\nObrigado pelo lembrete. Já acessamos o material no Google Drive (https://drive.google.com/projetoXPTO).\n\nCada responsável vai atualizar sua parte até quarta-feira, incluindo os slides de resultados financeiros e o gráfico de tendências.\n\nAssim teremos tempo de sobra para a revisão final na quinta.\n\n[]s,\nEquipe"
        },
        {
            "email": "Oi pessoal,\n\nVocês acreditam que esqueci a marmita em casa hoje? kkkkk\nAlguém topa pedir hambúrguer comigo no almoço?\n\nValeu,\nJoão",
            "category": "IMPRODUTIVO",
            "reason": "Assunto pessoal, sem relação com o trabalho.",
            "suggested_response": "Oi João,\nVamos combinar o almoço pessoalmente.\nNo email, seguimos focando nos temas de trabalho. :)"
        },
        {
            "email": "Gente,\n\nOlhem esse vídeo hilário que encontrei:\nhttps://youtu.be/123xyz 😂😂😂\n\nNão consigo parar de rir kkkk\n\nAbraços,\nPedro",
            "category": "IMPRODUTIVO",
            "reason": "Compartilhamento de entretenimento sem relevância profissional.",
            "suggested_response": "Oi Pedro,\nEsse tipo de conteúdo é melhor nos grupos informais.\nVamos manter o email apenas para trabalho."
        },
        {
            "email": "Oi,\n\nVocês viram a nova temporada daquela série que todo mundo acompanha? Achei o final meio forçado rsrs\n\nPodemos comentar no café da tarde!\n\nBjs,\nLuiza",
            "category": "IMPRODUTIVO",
            "reason": "Discussão de série de TV não tem relação com tarefas ou entregas.",
            "suggested_response": "Oi Luiza,\nCombinado, falamos da série no café.\nPor aqui seguimos só com os assuntos de trabalho. :)"
        },
        {
            "email": "Fala galera,\n\nBora pedir pizza na sexta? Quais sabores vcs curtem mais? 🍕\n\nAbs,\nThiago",
            "category": "IMPRODUTIVO",
            "reason": "Assunto de refeição, informal e sem relação com demandas da equipe.",
            "suggested_response": "Oi Thiago,\nMelhor alinharmos esse tipo de coisa pessoalmente.\nNo email seguimos só com trabalho."
        },
        {
            "email": "Oi,\n\nAlguém sabe se segunda é feriado municipal mesmo? Não queria vir à toa kkkkk\n\nValeu,\nAndré",
            "category": "IMPRODUTIVO",
            "reason": "Informação facilmente obtida em calendário oficial, não precisa ser discutida por email corporativo.",
            "suggested_response": "Oi André,\nConfirma no calendário oficial da empresa para ter certeza.\nAssim todos ficam alinhados."
        }
    ]

    username_line = f"Nome do usuario: {username}\n" if username else ""

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
        "- Leia o email com atenção para descobrir quem é o remetente e use o nome do usuário para assinar a resposta.\n"
        "- Leia o texto do email cuidadosamente para entender o contexto e detalhes importantes.\n"
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


_INFER_EXECUTOR = ThreadPoolExecutor(max_workers=IA_ASYNC_WORKERS)


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

