# main.py
import os, re, tempfile, json, subprocess, asyncio, traceback, logging, sys, uvicorn
from typing import List, Tuple, Optional
from dotenv import load_dotenv
from database import SessionLocal, init_db, User, Chat, Message
from faster_whisper import WhisperModel
from jira import JIRA, JIRAError
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta
from llm import get_llm
from sprint import replan_tasks_with_gemini, generate_tasks_with_gemini


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

logger = logging.getLogger("assistente-rag")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

MAX_CONCURRENT_ISSUES = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_ISSUES)

# --- Importações Langchain (conforme seu ambiente atual) ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import RetrievalQA

# ------------------ Config & Logging ------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("assistente-rag")

logger.info("Carregando configurações do .env...")
load_dotenv()

# --- Carregar Credenciais (fora de funções) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
api_key = os.getenv("GOOGLE_API_KEY")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
JIRA_BOARD_ID = os.getenv("JIRA_BOARD_ID")

# --- Configuráveis ---
PATH_VECTOR_DB = os.getenv("PATH_VECTOR_DB", "chroma_db")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-flash-latest")
RAG_RETRIEVER_K = int(os.getenv("RAG_RETRIEVER_K", "6"))
MAX_AUDIO_SECONDS = float(os.getenv("MAX_AUDIO_SECONDS", "120.0"))
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
EMBEDDINGS_DEVICE = os.getenv("EMBEDDINGS_DEVICE", "cpu")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# --- Validação básica das credenciais obrigatórias ---
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY não encontrada no .env")
if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
    raise EnvironmentError("Credenciais do JIRA não encontradas no .env")

# --- Prompts ---
PROMPT_ANALISTA_OCULTO_TEMPLATE = """
Sua tarefa é atuar como um Analista de Requisitos Sênior.
Com base no contexto (documentos de template e exemplos) e na solicitação do cliente abaixo,
gere uma lista de User Stories **em formato JSON válido**, seguindo rigorosamente as regras abaixo.

NÃO escreva nada fora do JSON.
NÃO inclua títulos, explicações ou texto adicional.
A resposta deve conter APENAS um objeto JSON.

-------------------------------------------
REGRAS DE FORMATAÇÃO DO JSON (OBRIGATÓRIAS)
-------------------------------------------

O JSON deve ter a estrutura:

{
  "user_stories": [
    {
      "id": "US-001",
      "title": "Título curto e claro",
      "story": {
        "role": "Como um: ...",
        "goal": "Eu quero: ...",
        "reason": "Para que: ..."
      },
      "acceptance_criteria": [
        "Critério 1",
        "Critério 2"
      ],
      "priority": "alta | media | baixa",
      "estimate": 1
    }
  ]
}

REGRAS ESTRITAS:
1. O JSON deve ser válido, sem vírgulas sobrando ou campos faltando.
2. IDs devem seguir padrão US-001, US-002, US-003...
3. Prioridades devem ser: "alta", "media" ou "baixa".
4. A estimativa deve ser um número inteiro (em story points).
5. Cada user story deve possuir **pelo menos 2 critérios de aceitação**.
6. "story" deve SEMPRE ter exatamente 3 campos:
   - role  (Como um:)
   - goal  (Eu quero:)
   - reason (Para que:)

-------------------------------------------
Solicitação do Cliente:
"{solicitacao_cliente}"
-------------------------------------------
"""

RAG_TEMPLATE = """
Contexto: {context}
---
Pergunta: {question}
---
Use o contexto para responder a pergunta. Se não souber, diga "Eu não sei". Responda em Português.
Resposta:
"""

REFINEMENT_PROMPT_TEMPLATE = """
Você deve refinar a última resposta do assistente com base no histórico e na nova instrução do usuário.
A resposta refinada deve ser **EXCLUSIVAMENTE um JSON válido**, seguindo exatamente o mesmo formato
do JSON de user stories utilizado anteriormente.

NÃO escreva nada fora do JSON.
NÃO inclua explicações, títulos, mensagens adicionais ou qualquer texto antes ou depois do JSON.

-------------------------------------------
Histórico da Conversa:
{historico_formatado}
-------------------------------------------

Nova instrução do usuário:
{instruction}

-------------------------------------------
REGRAS OBRIGATÓRIAS DO JSON
-------------------------------------------

O JSON final deve ter a estrutura exata:

{
  "user_stories": [
    {
      "id": "US-001",
      "title": "Título claro",
      "story": {
        "role": "Como um: ...",
        "goal": "Eu quero: ...",
        "reason": "Para que: ..."
      },
      "acceptance_criteria": [
        "Critério 1",
        "Critério 2"
      ],
      "priority": "alta | media | baixa",
      "estimate": 1
    }
  ]
}

REGRAS ESTRITAS (APLICAR NOVAMENTE):
1. A saída deve ser SOMENTE o objeto JSON.
2. A estrutura deve continuar idêntica ao schema acima.
3. IDs devem manter o padrão US-001, US-002...
4. Prioridade deve ser: "alta", "media" ou "baixa".
5. Estimativa deve ser um número inteiro.
6. Cada user story deve ter pelo menos 2 critérios de aceitação.
7. Campos "role", "goal" e "reason" devem manter o formato:
   - "Como um: ..."
   - "Eu quero: ..."
   - "Para que: ..."

Você deve reescrever o JSON completo com as modificações solicitadas.
"""

DOCUMENTATION_PROMPT_TEMPLATE = """
Você é um assistente técnico especializado em gerar **documentação de requisitos e funcionalidades**.

Use as informações fornecidas para criar um **documento técnico estruturado**, com as seguintes seções:

1. **Contexto do Projeto**
   - Explique o problema ou necessidade do cliente.
2. **Solução Proposta**
   - Descreva o que o sistema fará em termos gerais.
3. **Principais Funcionalidades**
   - Liste e detalhe as principais funcionalidades esperadas.
4. **Requisitos Funcionais**
   - Itens específicos que o sistema deve cumprir.
5. **Requisitos Não Funcionais**
   - Aspectos como desempenho, segurança, usabilidade, compatibilidade etc.
6. **Integrações e Dependências**
   - Sistemas externos, APIs, ou bancos de dados envolvidos.
7. **Considerações Técnicas**
   - Sugestões sobre arquitetura, tecnologias ou frameworks adequados.
8. **Próximos Passos**
   - O que deveria ser feito para seguir com o projeto.

---
**Informações do cliente:**
{client_request}

**Requisitos levantados:**
{requirements}
---
Gere um texto formal, objetivo e claro, sem listas genéricas. Organize com subtítulos e parágrafos.
"""

# --- Globals (inicializados na startup) ---
embeddings_model = None
vector_db = None
llm = None
qa_chain = None
whisper_model = None

# ------------------ Pydantic Models ------------------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ChatMessageCreate(BaseModel):
    user_id: int
    content: str
    sender: str = "user"
    chat_id: Optional[int] = None

class DocumentRequest(BaseModel):
    client_request: str
    requirements: str

class DocumentResponse(BaseModel):
    file_name: str
    file_path: str

# ------------------ DEPENDENCY ------------------

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------ Helpers & Utilities ------------------

def safe_print_exception(prefix: str, exc: Exception):
    logger.error("%s: %s", prefix, exc)
    logger.debug(traceback.format_exc())

@lru_cache(maxsize=1)
def get_jira_client_cached() -> JIRA:
    """Retorna um cliente JIRA cacheado."""
    logger.info("Criando cliente JIRA (cacheado).")
    return JIRA(server=JIRA_URL, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN), 
                options={'max_retries': 3, 'pool_connections': 60, 'pool_maxsize': 60})

def create_jira_issue_sync(issue_dict: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Função síncrona que cria issue no Jira. Retorna (key, title) ou (None, None) em erro.
    Executada em thread separado via asyncio.to_thread.
    """
    try:
        jira_client = get_jira_client_cached()
        new_issue = jira_client.create_issue(fields=issue_dict)
        return new_issue.key, issue_dict.get("summary", "")
    except JIRAError as e:
        logger.error("JIRAError ao criar issue: status=%s text=%s", getattr(e, "status_code", ""), getattr(e, "text", ""))
        return None, None
    except Exception as e:
        safe_print_exception("Erro geral ao criar issue JIRA", e)
        return None, None

def normalize_text_output(text: str) -> str:
    """
    Normaliza a saída do LLM para evitar problemas com formatação inesperada.
    Remove espaços duplicados, garante que títulos de seções estejam claros.
    """
    if not text:
        return text
    text = text.replace("\r\n", "\n").strip()
    # Remove múltiplas linhas em branco
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def split_requirements(text: str) -> List[dict]:

    import json
    if not text:
        return []

    try:
        data = json.loads(text)
        return data.get("user_stories", [])
    except json.JSONDecodeError:
        logger.warning("JSON inválido recebido do assistente.")
        return []

def run_blocking_in_thread(func, *args, **kwargs):
    """Helper para executar I/O/blocking em thread sem bloquear o loop principal."""
    return asyncio.to_thread(func, *args, **kwargs)

def get_audio_duration(path: str) -> float:
    """Retorna a duração em segundos usando ffprobe (síncrono)."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception("Não foi possível ler informações do áudio via ffprobe.")
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])

def get_whisper():
    """Inicializa e retorna (cache) o modelo Whisper local."""
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type="float32"
        )
        logger.info("Whisper carregado: %s", WHISPER_MODEL_SIZE)
    return whisper_model

# ------------------ Modelos Pydantic (mantidos como antes) ------------------

class ChatMessage(BaseModel):
    role: str
    content: str

class AnalysisRequest(BaseModel):
    client_request: str

class RefineRequest(BaseModel):
    instruction: str
    history: List[ChatMessage]

class ApproveRequest(BaseModel):
    final_requirements: str
    original_request: str

class AnalysisResponse(BaseModel):
    generated_requirements: str
    history: List[ChatMessage]

class RefineResponse(BaseModel):
    refined_requirements: str
    history: List[ChatMessage]

class ApproveResponse(BaseModel):
    message: str
    created_tickets: List[dict]
    invalid_requirements: list[dict] | None = None

# ------------------ FastAPI App & CORS ------------------

app = FastAPI(
    title="Assistente RAG de Requisitos",
    description="API para gerar, refinar e enviar requisitos para o Jira usando RAG.",
    version="0.4.0 (Melhorias de robustez)"
)

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Função para extrair palavra-chave contextual ---
def extrair_palavra_chave(texto: str) -> str:
    """
    Tenta capturar algo como:
    - 'sistema de vendas' → 'vendas'
    - 'aplicativo de pedidos' → 'pedidos'
    """
    match = re.search(r"\b(sistema|plataforma|app|aplicativo|dashboard)\s+de\s+(\w+)", texto, re.IGNORECASE)
    return match.group(2).lower() if match else "projeto"

# --- Função para gerar o PDF ---
def clean_text_for_pdf(text: str) -> str:
    cleaned = text

    # --- remover markdown de títulos (#, ##, ### etc)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)

    # --- remover negrito/itálico: **texto**, *texto*
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)

    # --- remover backticks `code`
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)

    # --- remover bullets (* algo ou - algo)
    cleaned = re.sub(r"^[\*\-]\s*", "", cleaned, flags=re.MULTILINE)

    # --- remover títulos tipo ### Texto
    cleaned = re.sub(r"^###\s*", "", cleaned, flags=re.MULTILINE)

    # --- remover links markdown [texto](url)
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)

    # --- remover múltiplos espaços
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)

    # --- normalizar quebras de linha
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # --- remover espaços no início da linha
    cleaned = re.sub(r"^[ \t]+", "", cleaned, flags=re.MULTILINE)

    return cleaned.strip()

def gerar_pdf(conteudo: str, caminho: str):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    story = []

    for paragrafo in conteudo.split("\n\n"):
        story.append(Paragraph(paragrafo, styles["Normal"]))
        story.append(Spacer(1, 12))

    doc.build(story)

# ------------------ Load Models & RAG Chain ------------------

def _validate_vector_db_path(path: str):
    if not Path(path).exists():
        raise FileNotFoundError(f"Diretório ChromaDB '{path}' não encontrado. Execute ingest.py primeiro.")

def load_models_and_chain():
    """
    Carrega embeddings, vector DB, LLM e a cadeia RAG.
    Executado na inicialização do app.
    """
    global embeddings_model, vector_db, llm, qa_chain
    logger.info("Carregando modelo de embeddings local...")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': EMBEDDINGS_DEVICE}
    )

    logger.info("Validando VectorDB em %s", PATH_VECTOR_DB)
    _validate_vector_db_path(PATH_VECTOR_DB)

    logger.info("Conectando ao Chroma DB...")
    vector_db = Chroma(
        persist_directory=PATH_VECTOR_DB,
        embedding_function=embeddings_model
    )

    logger.info("Inicializando LLM: %s", LLM_MODEL_NAME)
    llm = get_llm() 

    retriever = vector_db.as_retriever(search_kwargs={"k": RAG_RETRIEVER_K})
    rag_prompt = PromptTemplate(template=RAG_TEMPLATE, input_variables=["context", "question"])
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={"prompt": rag_prompt}
    )
    logger.info("Modelos e cadeia RAG carregados com sucesso!")

# ------------------ Rotas (mantidas) ------------------

@app.on_event("startup")
async def startup_event():
    """Executa a carga de modelos na inicialização (bloqueante - sucinta)."""
    try:
        load_models_and_chain()
    except Exception as e:
        safe_print_exception("Erro ao iniciar models/chain", e)
        # Não aborta o processo inteiro: mantem a app no ar para health check.
        # Endpoints que dependem da cadeia irão checar qa_chain e retornar 503.
        logger.warning("Inicialização incompleta; alguns endpoints podem retornar 503.")

@app.get("/")
async def read_root():
    return {"message": "API do Assistente RAG está online! Acesse /docs para interagir."}

@app.post("/start_analysis", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest):
    if not qa_chain:
        raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")
    logger.info("Recebida solicitação inicial: %s", (request.client_request[:120] + '...') if len(request.client_request) > 120 else request.client_request)

    prompt_completo = PROMPT_ANALISTA_OCULTO_TEMPLATE.replace("{solicitacao_cliente}", request.client_request)
    try:
        # invoke pode ser custoso - manter chamado síncrono via to_thread se necessário
        resposta_rag = await run_blocking_in_thread(qa_chain.invoke, {"query": prompt_completo})
        requisitos_gerados = normalize_text_output(resposta_rag.get("result", ""))
        history = [
            ChatMessage(role="user", content=request.client_request),
            ChatMessage(role="assistant", content=requisitos_gerados)
        ]
        logger.info("Análise inicial concluída.")
        return AnalysisResponse(generated_requirements=requisitos_gerados, history=history)
    except Exception as e:
        safe_print_exception("Erro durante /start_analysis", e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar análise inicial: {str(e)}")

@app.post("/refine", response_model=RefineResponse)
async def refine_requirements(request: RefineRequest):
    if not qa_chain:
        raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")
    logger.info("Recebida instrução de refinamento: %s", request.instruction[:120])

    historico_formatado = "\n".join([f"{msg.role}: {msg.content}" for msg in request.history])
    prompt_completo = (
    REFINEMENT_PROMPT_TEMPLATE
        .replace("{historico_formatado}", historico_formatado)
        .replace("{instruction}", request.instruction)
    )
    try:
        resposta_rag = await run_blocking_in_thread(qa_chain.invoke, {"query": prompt_completo})
        requisitos_refinados = normalize_text_output(resposta_rag.get("result", ""))
        new_history = request.history + [
            ChatMessage(role="user", content=request.instruction),
            ChatMessage(role="assistant", content=requisitos_refinados)
        ]
        logger.info("Refinamento concluído.")
        return RefineResponse(refined_requirements=requisitos_refinados, history=new_history)
    except Exception as e:
        safe_print_exception("Erro durante /refine", e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar refinamento: {str(e)}")

@app.post("/approve", response_model=ApproveResponse)
async def approve_and_send_to_jira(request: ApproveRequest):
    logger.info("Recebida solicitação de aprovação (aprovar->Jira).")

    # Extrair lista de user stories do JSON
    lista_de_requisitos = split_requirements(request.final_requirements)
    if not lista_de_requisitos:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma user story encontrada no JSON."
        )

    solicitacao_original = request.original_request
    tickets_criados = []
    erros = []

    async def criar_um_ticket(story: dict):
        titulo = story.get("title", "Requisito sem título")
        desc = (
            f"Solicitação Original do Cliente:\n{{quote}}\n{solicitacao_original}\n{{quote}}\n\n"
            "--- USER STORY DETALHADA ---\n\n"
            f"Role: {story.get('story', {}).get('role', '')}\n"
            f"Goal: {story.get('story', {}).get('goal', '')}\n"
            f"Reason: {story.get('story', {}).get('reason', '')}\n\n"
            f"Critérios de Aceitação:\n" + "\n".join(story.get("acceptance_criteria", [])) + "\n"
            f"Prioridade: {story.get('priority', '')}\n"
            f"Estimate: {story.get('estimate', '')}"
        )
        issue_dict = {
            'project': {'key': JIRA_PROJECT_KEY},
            'summary': titulo,
            'description': desc,
            'issuetype': {'name': 'Story'},
        }
        key, created_title = await run_blocking_in_thread(create_jira_issue_sync, issue_dict)
        return key, created_title

    # Criação paralela de tickets
    async def sem_task(story):
        async with asyncio.Lock():
            return await criar_um_ticket(story)

    tasks = [sem_task(story) for story in lista_de_requisitos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, Exception):
            safe_print_exception("Erro ao criar ticket (gather)", res)
            erros.append(str(res))
        elif res is None:
            erros.append("User story vazia")
        else:
            key, title = res
            if key:
                tickets_criados.append({"key": key, "title": title})
            else:
                erros.append(f"Falha ao criar ticket para: {title if title else 'sem título'}")

    msg = f"Processo concluído com {len(tickets_criados)} tickets criados."
    if erros:
        msg += f" {len(erros)} erros ocorreram."
        logger.warning(msg)
    else:
        logger.info(msg)

    return ApproveResponse(message=msg, created_tickets=tickets_criados)

@app.post("/audio_chat")
async def audio_chat(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    # Salvar temporariamente com suffix seguro
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_file = tmp.name

        duration = await run_blocking_in_thread(get_audio_duration, tmp_file)
        if duration > MAX_AUDIO_SECONDS:
            raise HTTPException(status_code=400, detail=f"Áudio muito longo: {duration:.1f}s (máximo {MAX_AUDIO_SECONDS:.0f}s).")

        wm = get_whisper()
        # transcrição (pode ser custosa) — executar em thread
        def _transcribe(path):
            segments, info = wm.transcribe(path)
            transcript = "".join(seg.text for seg in segments).strip()
            return transcript
        transcript = await run_blocking_in_thread(_transcribe, tmp_file)
        if not qa_chain:
            raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")
        response = await run_blocking_in_thread(qa_chain.invoke, {"query": transcript})
        llm_answer = normalize_text_output(response.get("result", ""))
        return {
            "duration_seconds": duration,
            "transcript": transcript,
            "llm_response": llm_answer
        }
    except HTTPException:
        raise
    except Exception as e:
        safe_print_exception("Erro durante /audio_chat", e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar áudio: {str(e)}")
    finally:
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                logger.debug("Falha ao remover arquivo temporário.")

@app.post("/cadastro")
def signup(user: UserCreate):
    db = SessionLocal()
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=User.hash_password(user.password)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"id": new_user.id, "name": new_user.name, "email": new_user.email}

@app.post("/login")
def login(user: UserLogin, db: SessionLocal = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not db_user.verify_password(user.password):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    # Podemos retornar token JWT mais tarde, mas por enquanto só id
    return {"id": db_user.id, "name": db_user.name, "email": db_user.email}

# ------------------ ROTAS DE CHAT/HISTÓRICO ------------------

@app.get("/chats")
def get_user_chats(user_id: int, db: SessionLocal = Depends(get_db)):
    """
    Retorna todos os chats do usuário com mensagens.
    """
    chats = db.query(Chat).filter(Chat.user_id == user_id).all()
    result = []
    for chat in chats:
        result.append({
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at,
            "messages": [{"sender": m.sender, "content": m.content, "created_at": m.created_at} for m in chat.messages]
        })
    return result

@app.post("/chat_message")
def add_chat_message(message: ChatMessageCreate, db: SessionLocal = Depends(get_db)):
    """
    Cria/atualiza chat e salva mensagem.
    - Se chat_id não informado, cria novo chat com título igual aos primeiros 50 caracteres da mensagem.
    """
    user_id = message.user_id
    content = message.content
    sender = message.sender
    chat_id = message.chat_id

    if chat_id:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat não encontrado")
    else:
        chat = Chat(user_id=user_id, title=content[:50])
        db.add(chat)
        db.commit()
        db.refresh(chat)

    msg = Message(chat_id=chat.id, sender=sender, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {"chat_id": chat.id, "message_id": msg.id, "sender": msg.sender, "content": msg.content}

@app.post("/generate_pdf")
async def generate_document(request: DocumentRequest):
    if not qa_chain:
        raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")

    logger.info("Recebida solicitação para gerar documentação técnica.")

    prompt_completo = DOCUMENTATION_PROMPT_TEMPLATE.format(
        client_request=request.client_request,
        requirements=request.requirements
    )

    try:
        resposta_rag = await run_blocking_in_thread(qa_chain.invoke, {"query": prompt_completo})
        conteudo = resposta_rag.get("result", "").strip()

        conteudo_limpo = clean_text_for_pdf(conteudo)

        # --- gerar PDF em memória ---
        pdf_buffer = BytesIO()
        gerar_pdf(conteudo_limpo, pdf_buffer)  # você só precisa alterar gerar_pdf pra aceitar um file-like
        pdf_buffer.seek(0)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=documentacao_requisitos.pdf"
            }
        )

    except Exception as e:
        safe_print_exception("Erro durante /generate_document", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar documentação: {str(e)}")

#---------------------- PLANEJAMENTO DE SPRINT ---------------------    

from sprint import replan_tasks_with_gemini, generate_tasks_with_gemini

class SprintPlanResponse(BaseModel):
    sprint_name: str
    tasks: list[dict]

class SprintRequest(BaseModel):
    messages: list[ChatMessage]

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

@app.post("/sprint/test-ruleset", response_model=SprintPlanResponse)
async def test_ruleset(request: SprintRequest):

    # 1. Última msg do assistant
    last_ai_message = next(
        (msg.content for msg in reversed(request.messages) if msg.role == "assistant"),
        None
    )

    if last_ai_message is None:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma mensagem do assistant encontrada no histórico."
        )

    # 2. Interpretar stories usando extract_json
    stories = extract_json(last_ai_message)
    if stories is None:
        raise HTTPException(
            status_code=400,
            detail=f"A última mensagem do assistant não contém JSON válido.\nConteúdo recebido:\n{last_ai_message}"
        )

    # 3. Chamar o modelo
    raw_tasks = await generate_tasks_with_gemini(stories)

    if not isinstance(raw_tasks, list):
        raise HTTPException(
            status_code=500,
            detail="Campo 'tasks' não é uma lista."
        )

    return SprintPlanResponse(
        sprint_name="Sprint Test",
        tasks=raw_tasks
    )

# REPLAN – IA replaneja as tasks existentes
class ReplanRequest(BaseModel):
    current_tasks: List[dict]
    instruction: str

class ReplanResponse(BaseModel):
    tasks: List[dict]

@app.post("/sprint/replan", response_model=ReplanResponse)
async def replan_sprint(request: ReplanRequest):
    """
    Replaneja a lista atual de tasks com base em uma instrução.
    """
    logger.info("Replanejamento solicitado: %s", request.instruction[:120])

    try:
        # 🔹 Chama função que já retorna lista de tasks limpa
        tasks = await replan_tasks_with_gemini(
            current_tasks=request.current_tasks,
            instruction=request.instruction
        )

        logger.info("Replanejamento concluído. %d tasks geradas.", len(tasks))

        return ReplanResponse(tasks=tasks)

    except Exception as e:
        safe_print_exception("Erro durante replanejamento", e)
        raise HTTPException(status_code=500, detail=f"Erro ao replanejar: {str(e)}")


# --- FUNÇÕES DE SPRINT ---
def create_sprint_rest(jira_client: JIRA, name: str, board_id: int, start: datetime, end: datetime):
    url = f"{jira_client._options['server']}/rest/agile/1.0/sprint"
    payload = {
        "name": name,
        "originBoardId": board_id,
        "startDate": start.isoformat() + "Z",
        "endDate": end.isoformat() + "Z"
    }
    response = jira_client._session.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def start_sprint_rest(jira_client: JIRA, board_id: int, sprint_id: int, start_date: datetime = None):
    url = f"{jira_client._options['server']}/rest/agile/1.0/board/{board_id}/sprint/{sprint_id}/start"
    payload = {}
    if start_date:
        payload["startDate"] = start_date.isoformat() + "Z"
    response = jira_client._session.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def create_jira_issue_sync_debug(issue_dict):
    """Cria uma issue no Jira e loga response resumido em caso de erro."""
    try:
        issue = jira_agile_client.create_issue(fields=issue_dict)
        return issue.key
    except Exception as e:
        msg = getattr(e, "response", None)
        if msg:
            try:
                resp_json = msg.json()
                logger.error("Erro ao criar issue: %s. Response: %s", e, resp_json)
            except Exception:
                logger.error("Erro ao criar issue: %s. Response não pôde ser convertido em JSON", e)
        else:
            logger.error("Erro ao criar issue (sem response): %s", e)
        raise e

# --- MODELOS DE REQUEST/RESPONSE ---
class SendSprintRequest(BaseModel):
    sprint_name: str
    created_at: str
    tasks: List[dict]

class SendSprintResponse(BaseModel):
    sprint_id: Optional[int]
    created_issues: List[dict]


EMAIL = os.getenv("EMAIL_JIRA")
jira_agile_client = JIRA(
    server=f"{JIRA_URL}",
    basic_auth=(EMAIL, JIRA_API_TOKEN)
)

# --- FUNÇÃO ASYNC PRINCIPAL ---
@app.post("/sprint/send_sprint_to_jira", response_model=SendSprintResponse)
async def send_sprint_to_jira(request: SendSprintRequest):
    logger.info("=== INÍCIO: Enviando sprint '%s' para Jira (%d tasks) ===", request.sprint_name, len(request.tasks))

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=14)
    sprint_id = None

    # 1️⃣ Criar sprint
    try:
        sprint_data = await asyncio.to_thread(
            lambda: create_sprint_rest(jira_agile_client, request.sprint_name, JIRA_BOARD_ID, start_date, end_date)
        )
        sprint_id = sprint_data.get("id")
        logger.info("Sprint criada com ID %s", sprint_id)
    except Exception as e:
        logger.warning("Não foi possível criar sprint: %s. Todas as tarefas irão para o backlog.", e)

    # 2️⃣ Aguardar e iniciar sprint
    if sprint_id:
        await asyncio.sleep(2)  # Delay curto para garantir que sprint esteja disponível
        try:
            await asyncio.to_thread(lambda: start_sprint_rest(jira_agile_client, JIRA_BOARD_ID, sprint_id, start_date))
            logger.info("Sprint %s iniciada com sucesso.", sprint_id)
        except Exception as e:
            logger.warning("Não foi possível iniciar sprint %s: %s. As tarefas ficarão no backlog.", sprint_id, e)
            sprint_id = None  # fallback para backlog

    created = []
    valid_keys = []

    # 3️⃣ Criar issues com limite de concorrência
    async def create_issue(task):
        async with semaphore:
            title = task.get("description") or "Tarefa sem descrição"
            desc = (
                f"Sprint: {request.sprint_name}\n"
                "--- TASK GERADA PELA IA ---\n"
                f"Descrição: {task.get('description')}\n"
                f"US ID: {task.get('us_id')}\n"
                f"US Title: {task.get('us_title')}\n"
                f"Estimativa: {task.get('estimate')}\n"
            )
            issue_dict = {
                'project': {'key': JIRA_PROJECT_KEY},
                'summary': title,
                'description': desc,
                'issuetype': {'name': 'Task'},
            }
            try:
                key = await asyncio.to_thread(lambda: create_jira_issue_sync_debug(issue_dict))
                return key.strip() if key else None
            except Exception as e:
                logger.warning("Erro ao criar issue '%s': %s", title, e)
                return None

    tasks_to_create = [create_issue(t) for t in request.tasks]
    issue_keys = await asyncio.gather(*tasks_to_create)
    valid_keys = [k for k in issue_keys if k]

    for key in valid_keys:
        created.append({"key": key})

    # 4️⃣ Adicionar issues à sprint ativa
    if sprint_id and valid_keys:
        try:
            await asyncio.to_thread(lambda: jira_agile_client.add_issues_to_sprint(sprint_id, valid_keys))
            logger.info("Todas as issues válidas adicionadas à sprint %s.", sprint_id)
        except Exception as e:
            logger.warning("Erro ao adicionar issues à sprint: %s. As tarefas ficarão no backlog.", e)

    logger.info("=== FIM: Sprint '%s' enviada ao Jira. %d issues criadas ===",
                request.sprint_name, len(valid_keys))

    return SendSprintResponse(sprint_id=sprint_id, created_issues=created)
# ------------------ Run (dev) ------------------

if __name__ == "__main__":
    logger.info("Iniciando servidor Uvicorn em http://127.0.0.1:8000")
    if qa_chain is None:
        try:
            load_models_and_chain()
        except Exception as e:
            safe_print_exception("Falha ao carregar modelos no __main__", e)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
