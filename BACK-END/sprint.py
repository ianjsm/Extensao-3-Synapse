import json
import asyncio
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from llm import get_llm

# Carregar .env
load_dotenv()
llm = get_llm()

def extract_json(text: str):
    # Remove demarcação de blocos ```json ... ```
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "")

    # Extrai o primeiro objeto JSON bem formado
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    
    try:
        return json.loads(match.group(0))
    except Exception:
        return None

# -----------------------------------------------------------------------------
# UTILITÁRIOS: carregar ruleset e helper para executar bloqueante no thread pool
# -----------------------------------------------------------------------------
def load_ruleset():
    path = Path(__file__).resolve().parent / "sprints" / "ruleset_sprint_planner_v1.md"
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de regras não encontrado: {path}")
    return path.read_text(encoding="utf-8")

async def run_blocking(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# -----------------------------------------------------------------------------
# Função principal adaptada: usa llm.invoke() do ChatGoogleGenerativeAI
# -----------------------------------------------------------------------------
async def generate_tasks_with_gemini(user_stories: list[dict]):
    ruleset = load_ruleset()
    user_stories_json = json.dumps(user_stories, indent=2, ensure_ascii=False)

    prompt = f"""
Você deve seguir as regras do sistema abaixo e responder APENAS com um JSON no formato especificado:

### REGRAS_DO_SISTEMA:
{ruleset}

### INPUT:
{user_stories_json}

Lembre-se: retorne apenas um objeto JSON com chave "tasks" contendo a lista de tasks.
"""

    def call_llm_sync():
        resp = llm.invoke(prompt)

        if isinstance(resp, str):
            return resp
        if hasattr(resp, "content"):
            return resp.content
        if hasattr(resp, "message") and hasattr(resp.message, "content"):
            return resp.message.content
        
        return str(resp)

    raw_output = await run_blocking(call_llm_sync)

    data = extract_json(raw_output)
    if data is None:
        raise RuntimeError(
            "Erro ao interpretar saída do Gemini/LangChain como JSON.\n"
            f"Saída recebida:\n{raw_output}"
        )

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("Formato inesperado: 'tasks' não é uma lista.")

    return tasks

async def replan_tasks_with_gemini(current_tasks, instruction):
    ruleset = load_ruleset()

    input_json = json.dumps({
        "instruction": instruction,
        "current_tasks": current_tasks
    }, ensure_ascii=False, indent=2)

    prompt = f"""
Você é um planejador de sprint que deve **modificar** o sprint existente,
seguindo as regras do sistema e respeitando ao máximo o trabalho já planejado.

### REGRAS DO SISTEMA
{ruleset}

### CONTEXTO PARA REPLANEJAMENTO
{input_json}

Sua tarefa:
- Ajustar, remover, adicionar ou reestimar tasks conforme a instrução dada.
- Manter a coerência, consistência e granularidade do sprint já existente.
- Responder apenas com JSON no formato:
{{
  "tasks": [ ... ]
}}
"""

    def call_sync():
        resp = llm.invoke(prompt)
        if isinstance(resp, str):
            return resp
        if hasattr(resp, "content"):
            return resp.content
        if hasattr(resp, "message") and hasattr(resp.message, "content"):
            return resp.message.content
        return str(resp)

    raw_output = await run_blocking(call_sync)

    # 🔹 Garante que sai JSON válido
    data = extract_json(raw_output)
    if data is None:
        raise RuntimeError(f"Saída inválida do Gemini/LangChain:\n{raw_output}")

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError(f"'tasks' não é lista:\n{data}")

    return tasks