from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import json, asyncio, os, requests
from dotenv import load_dotenv

router = APIRouter()

# --- MODELOS ---

class StoryStory(BaseModel):
    role: str
    goal: str
    reason: str

class UserStory(BaseModel):
    id: str
    title: str
    story: StoryStory
    acceptance_criteria: List[str]
    priority: str
    estimate: int

class SprintRequest(BaseModel):
    user_stories: List[UserStory]

class Task(BaseModel):
    id: str
    description: str
    us_id: str
    us_title: str
    estimate: int

class SprintResponse(BaseModel):
    sprint_name: str
    tasks: List[Task]

# --- HELPERS ---

def run_blocking_in_thread(func, *args, **kwargs):
    """Executa função bloqueante em thread sem travar o loop principal."""
    return asyncio.to_thread(func, *args, **kwargs)

def get_qa_chain():
    """Garante que o QA chain esteja carregado."""
    from main import qa_chain, load_models_and_chain
    if qa_chain is None:
        load_models_and_chain()
    return qa_chain

# --- GERAÇÃO DE TASKS USANDO IA ---

async def generate_tasks_from_us(user_stories: List[UserStory]):
    qa = get_qa_chain()
    
    us_list_str = json.dumps([us.dict() for us in user_stories], indent=2)
    prompt = f"""
Você é um especialista em planejamento de sprints.
Gere uma lista de tarefas técnicas a partir das seguintes User Stories:

{us_list_str}

Cada tarefa deve ter:
  - descrição
  - us_id (referência da User Story)
  - us_title
  - estimate (em pontos)

Retorne tudo em um único JSON com a chave "tasks", assim:
{{
  "tasks": [
    {{"description": "...", "us_id": "...", "us_title": "...", "estimate": ...}}
  ]
}}
"""

    # chamada à IA
    resposta = await run_blocking_in_thread(qa.invoke, {"query": prompt})
    resultado = resposta.get("result", "").strip()

    tasks = []
    task_counter = 1
    try:
        data = json.loads(resultado)
        for t in data.get("tasks", []):
            t["id"] = f"T-{task_counter:03}"
            tasks.append(Task(**t))
            task_counter += 1
    except Exception:
        # fallback: cada critério vira uma task
        task_counter = 1
        for us in user_stories:
            for i, criteria in enumerate(us.acceptance_criteria, 1):
                tasks.append(Task(
                    id=f"T-{task_counter:03}",
                    description=f"{criteria} (implementação da US {us.id})",
                    us_id=us.id,
                    us_title=us.title,
                    estimate=max(1, us.estimate // len(us.acceptance_criteria))
                ))
                task_counter += 1

    return tasks

# Carrega variáveis do .env
load_dotenv()
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

def create_jira_issue(task):
    """
    Cria uma issue no JIRA a partir de uma task.
    """
    url = f"{JIRA_URL}/rest/api/3/issue"
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    
    # Dados da issue
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"{task.us_id} - {task.us_title}: {task.description[:50]}",
            "description": f"Task detalhada da US {task.us_id}\n\n{task.description}",
            "issuetype": {"name": "Task"},
            "customfield_10016": task.estimate  # Story points, ajuste se necessário
        }
    }
    
    resp = requests.post(url, json=payload, auth=auth)
    resp.raise_for_status()
    return resp.json()

# --- ENDPOINT ---

@router.post("/generate_sprint", response_model=SprintResponse)
async def generate_sprint(request: SprintRequest):
    try:
        tasks = await generate_tasks_from_us(request.user_stories)
        return SprintResponse(
            sprint_name="Sprint 1",
            tasks=tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar sprint: {str(e)}")

@router.post("/send_sprint_to_jira")
async def send_sprint_to_jira(sprint: SprintResponse):
    """
    Recebe as tasks da sprint e cria issues no JIRA.
    Retorna lista de issues criadas.
    """
    created_issues = []
    errors = []

    for task in sprint.tasks:
        try:
            issue = create_jira_issue(task)
            created_issues.append(issue.get("key"))
        except Exception as e:
            errors.append(f"{task.id} ({task.us_id}): {str(e)}")

    return {
        "created_issues": created_issues,
        "errors": errors
    }