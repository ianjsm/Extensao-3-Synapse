import os
import re
import tempfile
from dotenv import load_dotenv
from jira import JIRA, JIRAError
from fastapi import FastAPI, HTTPException # <- FastAPI
from pydantic import BaseModel # <- Para definir modelos de dados da API
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# --- Importações Langchain (que sabemos que funcionam) ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import RetrievalQA
# --------------------------------------------------------

print("Carregando configurações do .env...")
load_dotenv()

# --- Carregar Credenciais (fora de funções) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# --- Validação de Chaves (fora de funções) ---
if not GOOGLE_API_KEY: raise EnvironmentError("GOOGLE_API_KEY não encontrada.")
if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
    raise EnvironmentError("Credenciais do JIRA não encontradas no .env")

# --- Constantes (fora de funções) ---
PATH_VECTOR_DB = "chroma_db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL_NAME = "gemini-flash-latest" # <-- CORRIGIDO
PROMPT_ANALISTA_OCULTO_TEMPLATE = """
Sua tarefa é atuar como um Analista de Requisitos Sênior. 
Com base no contexto (documentos de template e exemplos) e na solicitação do cliente abaixo, gere uma lista detalhada de Requisitos Funcionais como User Stories (formato "Como um...", "Eu quero...", "Para que...") com Critérios de Aceite.
---
Solicitação do Cliente: "{solicitacao_cliente}"
---
Requisitos Gerados:
"""
RAG_TEMPLATE = """
Contexto: {context}
---
Pergunta: {question}
---
Use o contexto para responder a pergunta. Se não souber, diga "Eu não sei". Responda em Português.
Resposta:
"""
# --- PROMPT DE REFINAMENTO ATUALIZADO (Sem separador) ---
REFINEMENT_PROMPT_TEMPLATE = """
Histórico da conversa:
---
{historico_formatado}
---
Nova instrução do usuário: {instruction}
---
Com base no histórico e na nova instrução, refine a última resposta do assistente ou adicione o que foi pedido.
Responda apenas com a lista de requisitos atualizada e formatada corretamente no formato User Story.
"""

# --- Globais da Aplicação (serão carregadas na inicialização) ---
embeddings_model = None
vector_db = None
llm = None
qa_chain = None
# -------------------------------------------------------------

# --- Funções Auxiliares (movidas do script antigo) ---

def load_models_and_chain():
    """ Carrega os modelos e a cadeia RAG uma vez na inicialização. """
    global embeddings_model, vector_db, llm, qa_chain # Permite modificar as globais
    
    print("Carregando modelo de embeddings local...")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'}
    )

    print(f"Carregando VectorDB de: {PATH_VECTOR_DB}")
    if not os.path.exists(PATH_VECTOR_DB):
         raise FileNotFoundError(f"Diretório ChromaDB '{PATH_VECTOR_DB}' não encontrado. Execute ingest.py primeiro.")
    vector_db = Chroma(
        persist_directory=PATH_VECTOR_DB,
        embedding_function=embeddings_model
    )

    print(f"Carregando LLM: {LLM_MODEL_NAME}")
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL_NAME,
        temperature=0.3,
        google_api_key=GOOGLE_API_KEY
    )

    retriever = vector_db.as_retriever(search_kwargs={"k": 6})

    print("Criando a cadeia RAG (RetrievalQA)...")
    rag_prompt = PromptTemplate(
        template=RAG_TEMPLATE,
        input_variables=["context", "question"]
    )
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False, # Não precisamos mais das fontes na API
        chain_type_kwargs={"prompt": rag_prompt}
    )
    print("--- Modelos e Cadeia RAG carregados com sucesso! ---")

def criar_story_no_jira(texto_requisito, solicitacao_original):
    """ Cria uma única "Story" (Estória) no Jira. """
    try:
        jira_client = JIRA(server=JIRA_URL, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
        
        # --- REGEX DE TÍTULO MELHORADO ---
        # Procura por "Eu quero: [texto]" (com ou sem asteriscos, ignorando case)
        match = re.search(r"Eu quero:\s*\**\s*(.*)", texto_requisito, re.IGNORECASE)
        
        if match:
            titulo = match.group(1).strip().split('\n')[0] # Pega só a primeira linha do "Eu quero"
        else:
            # Título alternativo se a regex falhar
            primeira_linha = texto_requisito.split('\n')[0]
            titulo = f"Req: {primeira_linha[:60]}..." if primeira_linha else "Novo Requisito s/ Título"

        issue_dict = {
            'project': {'key': JIRA_PROJECT_KEY},
            'summary': titulo,
            'description': (
                f"Solicitação Original do Cliente:\n{{quote}}\n{solicitacao_original}\n{{quote}}\n\n"
                "--- REQUISITO DETALHADO ---\n\n"
                f"{texto_requisito}"
            ),
            'issuetype': {'name': 'Story'},
        }
        
        print(f"-> Criando ticket: {titulo}")
        new_issue = jira_client.create_issue(fields=issue_dict)
        return new_issue.key, titulo # Retorna chave E título
        
    except JIRAError as e: 
        print(f"--- ERRO JIRA: Status {e.status_code} ---")
        print(f"Verifique se o tipo 'Story' existe no projeto '{JIRA_PROJECT_KEY}'.")
        print(f"Resposta do Servidor: {e.text}")
        return None, None
    except Exception as e: 
        print(f"Erro Geral JIRA: {e}"); 
        return None, None

# --- Modelos de Dados Pydantic para a API ---

class ChatMessage(BaseModel):
    """ Representa uma única mensagem no histórico. """
    role: str # 'user' ou 'assistant'
    content: str

class AnalysisRequest(BaseModel):
    """ O que a API espera para iniciar a análise. """
    client_request: str

class RefineRequest(BaseModel):
    """ O que a API espera para refinar. """
    instruction: str
    history: list[ChatMessage] # Recebe o histórico anterior

class ApproveRequest(BaseModel):
     """ O que a API espera para aprovar. """
     final_requirements: str
     original_request: str

class AnalysisResponse(BaseModel):
    """ O que a API retorna após a análise inicial. """
    generated_requirements: str
    history: list[ChatMessage] # Retorna o histórico atualizado

class RefineResponse(BaseModel):
    """ O que a API retorna após o refinamento. """
    refined_requirements: str
    history: list[ChatMessage] # Retorna o histórico atualizado

class ApproveResponse(BaseModel):
    """ O que a API retorna após a aprovação. """
    message: str
    created_tickets: list[dict] # Lista de {key: 'SCRUM-X', title: '...'}

# --- Aplicação FastAPI ---

app = FastAPI(
    title="Assistente RAG de Requisitos",
    description="API para gerar, refinar e enviar requisitos para o Jira usando RAG.",
    version="0.3.0 (Split Robusto)" # Versão atualizada
)

# --- Configuração do CORS ---
# Define quais "origens" (sites) podem fazer requisições para esta API

origins = [
    "http://localhost:5173", # A porta padrão do Vite/React
    "http://localhost:5174", # Outra porta comum do Vite
    "http://localhost:3000", # Porta comum do create-react-app
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Permite as origens listadas
    allow_credentials=True,    # Permite cookies (se usarmos no futuro)
    allow_methods=["*"],         # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],         # Permite todos os cabeçalhos
)
# --- Fim da Configuração do CORS ---

# --- Evento de Inicialização ---
@app.on_event("startup")
async def startup_event():
    """ Código a ser executado quando a API inicia. """
    load_models_and_chain() # Carrega tudo uma única vez

# --- Endpoints da API ---

@app.get("/")
async def read_root():
    """ Endpoint inicial para verificar se a API está online. """
    return {"message": "API do Assistente RAG está online! Acesse /docs para interagir."}

@app.post("/start_analysis", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest):
    """ Endpoint para iniciar a análise a partir do texto do cliente. """
    if not qa_chain:
        raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")
    
    print(f"Recebida solicitação inicial: {request.client_request[:100]}...")
    
    prompt_completo = PROMPT_ANALISTA_OCULTO_TEMPLATE.format(
        solicitacao_cliente=request.client_request
    )
    
    try:
        resposta_rag = qa_chain.invoke({"query": prompt_completo})
        requisitos_gerados = resposta_rag["result"]
        
        # Cria o histórico inicial para retornar ao frontend
        history = [
            ChatMessage(role="user", content=request.client_request), # Aqui salvamos o texto original
            ChatMessage(role="assistant", content=requisitos_gerados)
        ]
        
        print("Análise inicial concluída.")
        return AnalysisResponse(generated_requirements=requisitos_gerados, history=history)

    except Exception as e:
        print(f"Erro durante /start_analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar análise inicial: {e}")

@app.post("/refine", response_model=RefineResponse)
async def refine_requirements(request: RefineRequest):
    """ Endpoint para refinar os requisitos com base no histórico. """
    if not qa_chain:
         raise HTTPException(status_code=503, detail="Cadeia RAG não inicializada.")

    print(f"Recebida instrução de refinamento: {request.instruction}")

    # Formata o histórico recebido para o prompt
    historico_formatado = "\n".join([f"{msg.role}: {msg.content}" for msg in request.history])
    
    # --- USA O NOVO PROMPT DE REFINAMENTO ---
    prompt_completo = REFINEMENT_PROMPT_TEMPLATE.format(
        historico_formatado=historico_formatado,
        instruction=request.instruction
    )

    try:
        resposta_rag = qa_chain.invoke({"query": prompt_completo})
        requisitos_refinados = resposta_rag["result"]

        # Adiciona a interação atual ao histórico
        new_history = request.history + [
            ChatMessage(role="user", content=request.instruction),
            ChatMessage(role="assistant", content=requisitos_refinados)
        ]

        print("Refinamento concluído.")
        return RefineResponse(refined_requirements=requisitos_refinados, history=new_history)

    except Exception as e:
        print(f"Erro durante /refine: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar refinamento: {e}")

@app.post("/approve", response_model=ApproveResponse)
async def approve_and_send_to_jira(request: ApproveRequest):
    """ Endpoint para aprovar e enviar os requisitos finais para o Jira. """
    print("Recebida solicitação de aprovação...")

    requisitos_finais = request.final_requirements
    solicitacao_original = request.original_request

    # --- LÓGICA DE SPLIT ROBUSTA (ATUALIZADA) ---
    print("Dividindo requisitos usando o marcador 'Como um:'...")
    
    # Divide a string ANTES de cada ocorrência de "**Como um:**" (ignorando case)
    # O '(?=...)' é um "lookahead" que divide sem consumir o separador.
    separador_regex = r'\s*(?=\*\*Como um:\*\*)'
    lista_de_requisitos_bruta = re.split(separador_regex, requisitos_finais, flags=re.IGNORECASE)
    
    # Filtra itens vazios e o cabeçalho (que não começa com "**Como um:")
    lista_de_requisitos = [
        req.strip() for req in lista_de_requisitos_bruta 
        if req.strip().lower().startswith("**como um:**")
    ]
    # --- FIM DA LÓGICA DE SPLIT ---

    print(f"Encontrados {len(lista_de_requisitos)} requisitos válidos para criar.")

    if not lista_de_requisitos:
         raise HTTPException(status_code=400, detail="Nenhum requisito no formato 'Como um:** ...' foi encontrado. A resposta do LLM pode estar mal formatada.")

    print(f"Iniciando criação de {len(lista_de_requisitos)} tickets no Jira...")

    tickets_criados = []
    erros = []

    for req in lista_de_requisitos:
        req_limpo = req.strip()
        if req_limpo:
            print(f"\n-> Processando requisito: '{req_limpo[:60]}...'")
            key, titulo = criar_story_no_jira(req_limpo, solicitacao_original)
            if key:
                tickets_criados.append({"key": key, "title": titulo})
            else:
                erros.append(f"Falha ao criar ticket para: '{req_limpo[:60]}...'")

    if erros:
        msg = f"Processo concluído com {len(erros)} erros e {len(tickets_criados)} sucessos."
        print(msg); print("\n".join(erros))
        return ApproveResponse(message=msg, created_tickets=tickets_criados)
    else:
        msg = f"Sucesso! {len(tickets_criados)} tickets criados no Jira."
        print(msg)
        return ApproveResponse(message=msg, created_tickets=tickets_criados)

# --- Bloco para rodar localmente ---
if __name__ == "__main__":
    print("Iniciando servidor Uvicorn em http://127.0.0.1:8000")
    # Garante que os modelos sejam carregados antes de iniciar o servidor Uvicorn
    if qa_chain is None:
        load_models_and_chain()
        
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)