# main.py
import os
import re
import tempfile
import json
import subprocess
import asyncio
import traceback
from typing import List, Tuple, Optional
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from jira import JIRA, JIRAError
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import logging
from functools import lru_cache
from pathlib import Path
import logging
import sys

logger = logging.getLogger("assistente-rag")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

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
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

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
Com base no contexto (documentos de template e exemplos) e na solicitação do cliente abaixo, gere uma lista de Requisitos Funcionais como User Stories.

**REGRAS ESTRITAS DE FORMATAÇÃO:**
1.  **NÃO** inclua nenhum título, cabeçalho, introdução ou texto de conclusão. Sua resposta deve começar IMEDIATAMENTE com o primeiro "**Como um:**".
2.  Cada User Story DEVE seguir o formato: "**Como um:**...", "**Eu quero:**...", "**Para que:**...".
3.  CADA User Story DEVE ter uma seção "**Critérios de Aceite:**" com pelo menos 2 critérios.

---
Solicitação do Cliente: "{solicitacao_cliente}"
---
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
Histórico da conversa:
---
{historico_formatado}
---
Nova instrução do usuário: {instruction}
---
Com base no histórico e na nova instrução, refine a última resposta do assistente.

**REGRAS ESTRITAS DE FORMATAÇÃO (APLIQUE NOVAMENTE):**
1.  **NÃO** inclua nenhum título, cabeçalho, introdução ou texto de conclusão. Sua resposta deve começar IMEDIATAMENTE com o primeiro "**Como um:**".
2.  Cada User Story DEVE seguir o formato: "**Como um:**...", "**Eu quero:**...", "**Para que:**...".
3.  CADA User Story DEVE ter uma seção "**Critérios de Aceite:**" com pelo menos 2 critérios.
"""

# --- Globals (inicializados na startup) ---
embeddings_model = None
vector_db = None
llm = None
qa_chain = None
whisper_model = None

# ------------------ Helpers & Utilities ------------------

def safe_print_exception(prefix: str, exc: Exception):
    logger.error("%s: %s", prefix, exc)
    logger.debug(traceback.format_exc())

@lru_cache(maxsize=1)
def get_jira_client_cached() -> JIRA:
    """Retorna um cliente JIRA (cacheado) — criação rápida e reutilizável."""
    logger.info("Criando cliente JIRA (cacheado).")
    return JIRA(server=JIRA_URL, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))

def formatar_para_jira(texto_md: str) -> str:
    """
    Traduz uma string de Markdown simples para o formato Jira Wiki Markup.
    """
    if not texto_md:
        return ""

    texto_jira = texto_md

    # 1. Títulos: Converte "## Título" para "h2. Título"
    texto_jira = re.sub(r"^\s*##\s*(.*)", r"h2. \1", texto_jira, flags=re.MULTILINE)

    # 2. Negrito: Converte "**texto**" para "*texto*"
    # (Usando ._? para ser "não-ganancioso" e pegar o par correto)
    texto_jira = re.sub(r"\*\*(.*?)\*\*", r"*\1*", texto_jira)

    # 3. Listas Numeradas: Converte "1. item" para "# item"
    texto_jira = re.sub(r"^\s*(\d+)\.\s+", r"# ", texto_jira, flags=re.MULTILINE)

    # 4. Linhas Horizontais: Converte "---" para "----"
    texto_jira = re.sub(r"^\s*---\s*$", r"----", texto_jira, flags=re.MULTILINE)

    # 5. (Opcional) Itálico: Converte "*texto*" para "_texto_"
    # Vamos converter os itálicos do LLM em negrito do Jira para destaque
    texto_jira = re.sub(r"\*(.*?)\*", r"*\1*", texto_jira) 

    return texto_jira.strip()

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

def split_requirements(text: str) -> List[str]:
    """
    Separa requisitos/estórias mesmo que o LLM use formatos variados.
    Aceita variações como:
      - **Como um:**
      - Como um:
      - Como um -
      - *Como um*
    Retorna lista de blocos que começam com 'Como um'.
    """
    text = normalize_text_output(text)
    # Tornar uniforme: substitui variantes por um marcador único
    standardized = re.sub(r"(?i)\*{0,2}\s*Como um[:\-\*]*\s*", "\n\n**Como um:** ", text)
    # Agora split por marcador que colocamos (mantendo marcador nos itens)
    parts = [p.strip() for p in re.split(r"\n\s*(?=\*\*Como um:\*\*)", standardized) if p.strip()]
    # Garantir que cada item comece com '**Como um:**' e retornar
    cleaned = []
    for p in parts:
        if p.lower().startswith("**como um:**"):
            cleaned.append(p)
        elif p.lower().startswith("como um"):
            cleaned.append("**" + p + "**")
        else:
            # Pode ser texto introdutório: anexar ao último se existir
            if cleaned:
                cleaned[-1] += "\n\n" + p
            else:
                # criar um bloco genérico
                cleaned.append(p)
    return cleaned

def extract_title_from_requirement(text: str) -> str:
    """
    Extrai um título curto a partir do campo 'Eu quero:' ou da primeira linha.
    """
    # Tentar localizar "Eu quero:" (com ou sem formatação)
    m = re.search(r"(?i)Eu quero[:\s\-]*\**\s*(.+)", text)
    if m:
        candidate = m.group(1).split("\n")[0].strip()
        return candidate[:120]
    # fallback para primeira linha relevante
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return "Requisito sem título"

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
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL_NAME,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        google_api_key=GOOGLE_API_KEY
    )

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

    prompt_completo = PROMPT_ANALISTA_OCULTO_TEMPLATE.format(solicitacao_cliente=request.client_request)
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
    prompt_completo = REFINEMENT_PROMPT_TEMPLATE.format(
        historico_formatado=historico_formatado,
        instruction=request.instruction
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
    requisitos_finais = request.final_requirements
    solicitacao_original = request.original_request

    logger.info("Dividindo requisitos gerados pelo LLM...")
    lista_de_requisitos = split_requirements(requisitos_finais)
    logger.info("Encontrados %d requisitos (após split).", len(lista_de_requisitos))

    if not lista_de_requisitos:
        raise HTTPException(status_code=400, detail="Nenhum requisito reconhecido no formato 'Como um'. Verifique a formatação da resposta do LLM.")

    # --- VALIDADOR AUTOMÁTICO ANTES DE CRIAR TICKETS ---
    validos = []
    invalidos = []

    for req in lista_de_requisitos:
        texto = req.lower()

        falta_como_um = "como um" not in texto
        falta_criterios = "critério de aceite" not in texto and "critérios de aceite" not in texto

        if falta_como_um or falta_criterios:
            invalidos.append({
                "requisito": req,
                "erro_como_um": falta_como_um,
                "erro_criterios": falta_criterios
            })
        else:
            validos.append(req)

    # Se houver inválidos, NÃO cria tickets — devolve relatório ao frontend
    if invalidos:
        return ApproveResponse(
            message="Alguns requisitos precisam ser revisados antes de enviar ao Jira.",
            created_tickets=[],
            invalid_requirements=invalidos  # você adiciona esse campo no schema
        )

    # Se todos passaram, segue com a criação normal
    lista_de_requisitos = validos

    tickets_criados = []
    erros = []

    async def criar_um_ticket(req_text: str):
        req_limpo = req_text.strip()
        if not req_limpo:
            return None
        titulo = extract_title_from_requirement(req_limpo)
        issue_dict = {
            'project': {'key': JIRA_PROJECT_KEY},
            'summary': titulo,
            'description': (
                f"Solicitação Original do Cliente:\n{{quote}}\n{solicitacao_original}\n{{quote}}\n\n"
                "--- REQUISITO DETALHADO ---\n\n"
                f"{req_limpo}"
            ),
            'issuetype': {'name': 'Story'},
        }
        # Criar em thread para não bloquear
        key, created_title = await run_blocking_in_thread(create_jira_issue_sync, issue_dict)
        return key, created_title

    # Criar tickets em paralelo (limitado)
    semaphore = asyncio.Semaphore(int(os.getenv("JIRA_CONCURRENCY", "4")))
    async def sem_task(req):
        async with asyncio.Lock():  # evita race com client cache; JIRA lib não é totalmente async safe
            return await criar_um_ticket(req)

    tasks = []
    for req in lista_de_requisitos:
        tasks.append(sem_task(req))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            safe_print_exception("Erro ao criar ticket (gather)", res)
            erros.append(str(res))
        elif res is None:
            erros.append("Requisito vazio")
        else:
            key, title = res
            if key:
                tickets_criados.append({"key": key, "title": title})
            else:
                erros.append(f"Falha ao criar ticket para: {title if title else 'sem título'}")

    if erros:
        msg = f"Processo concluído com {len(erros)} erros e {len(tickets_criados)} sucessos."
        logger.warning(msg)
        return ApproveResponse(message=msg, created_tickets=tickets_criados)
    else:
        msg = f"Sucesso! {len(tickets_criados)} tickets criados no Jira."
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

# ------------------ Run (dev) ------------------

if __name__ == "__main__":
    logger.info("Iniciando servidor Uvicorn em http://127.0.0.1:8000")
    if qa_chain is None:
        try:
            load_models_and_chain()
        except Exception as e:
            safe_print_exception("Falha ao carregar modelos no __main__", e)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
