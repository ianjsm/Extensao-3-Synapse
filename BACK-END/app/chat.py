import os
import re
import whisper # <- NOVO: Importa a biblioteca Whisper
from dotenv import load_dotenv
from jira import JIRA, JIRAError
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import RetrievalQA

print("Carregando configurações...")
load_dotenv()

# --- Carregar Credenciais do .env ---
# (Credenciais do Google e Jira como antes)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# --- Validação de Chaves ---
# (Validações como antes)
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY não encontrada no arquivo .env")
if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
    raise EnvironmentError("Credenciais do JIRA (URL, USERNAME, API_TOKEN, PROJECT_KEY) não encontradas no .env")

PATH_VECTOR_DB = "chroma_db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL_NAME = "gemini-flash-latest"

# --- Prompts (como antes) ---
PROMPT_ANALISTA_OCULTO = """
Sua tarefa é atuar como um Analista de Requisitos Sênior. 
Com base no contexto (documentos de template e exemplos) e na solicitação do cliente abaixo, gere uma lista detalhada de Requisitos Funcionais.

Formate os Requisitos Funcionais como User Stories (usando o template "Como um...", "Eu quero...", "Para que...") e inclua Critérios de Aceite claros para cada um.

**Importante:** No final de CADA User Story (incluindo seus critérios de aceite), insira o separador:
---[NOVO REQUISITO]---
---
Solicitação do Cliente:
"{solicitacao_cliente}"
---

Requisitos Gerados:
"""

RAG_TEMPLATE = """
Use a informação de contexto a seguir para responder a pergunta no final.
Se você não sabe a resposta com base no contexto, apenas diga "Eu não sei".
Responda em Português.

Contexto:
{context}

Pergunta:
{question}

Resposta:
"""

# --- Funções do Jira (como antes) ---
def criar_story_no_jira(texto_requisito, solicitacao_original):
    """ Cria uma única "Story" (Estória) no Jira. """
    try:
        # (Código da função criar_story_no_jira como antes)
        print(f"\nConectando ao Jira para criar Story...")
        jira_client = JIRA(
            server=JIRA_URL,
            basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN)
        )
        match = re.search(r"Eu quero:\*\* (.*)", texto_requisito)
        if match:
            titulo = match.group(1).strip()
        else:
            primeira_linha = texto_requisito.split('\n')[0]
            titulo = f"Req: {primeira_linha[:60]}..." if primeira_linha else f"Novo Requisito s/ Título"

        issue_dict = {
            'project': {'key': JIRA_PROJECT_KEY},
            'summary': titulo,
            'description': (
                f"Este requisito foi gerado a partir da solicitação:\n{{quote}}\n{solicitacao_original}\n{{quote}}\n\n"
                "--- REQUISITO DETALHADO ---\n\n"
                f"{texto_requisito}"
            ),
            'issuetype': {'name': 'Story'},
        }
        print(f"-> Projeto: {JIRA_PROJECT_KEY}, Tipo: Story, Título: {titulo}")
        print(f"-> Enviando dados para o Jira...")
        new_issue = jira_client.create_issue(fields=issue_dict)
        print(f"-> Sucesso! Story criada: {new_issue.key} - {titulo}")
        return new_issue.key
    except JIRAError as e:
        print(f"--- ERRO DETALHADO DO JIRA (JIRAError) ---")
        print(f"Status Code: {e.status_code}")
        print(f"Texto da Resposta do Servidor Jira:\n{e.text}")
        print("\nCausas comuns: URL/Credenciais/Permissões/Project Key/Issue Type incorretos.")
        return None
    except Exception as e:
        print(f"--- ERRO GERAL AO CRIAR STORY NO JIRA ---")
        print(f"Erro: {e}, Tipo: {type(e)}")
        return None

# --- NOVA FUNÇÃO: Transcrição com Whisper ---
def transcrever_audio_com_whisper(caminho_arquivo):
    """
    Transcreve um arquivo de áudio usando o Whisper localmente.
    Retorna o texto transcrito ou None em caso de erro.
    """
    try:
        print(f"\nCarregando modelo Whisper (pode levar um tempo na primeira vez)...")
        # Use 'tiny', 'base', 'small', 'medium', or 'large'.
        # Modelos menores são mais rápidos, maiores são mais precisos.
        # 'base' é um bom ponto de partida.
        model = whisper.load_model("base")
        print(f"Transcrevendo áudio de: {caminho_arquivo}...")
        
        # Realiza a transcrição
        result = model.transcribe(caminho_arquivo, fp16=False) # fp16=False para melhor compatibilidade com CPU
        
        texto_transcrito = result["text"]
        print("Transcrição concluída.")
        return texto_transcrito
        
    except FileNotFoundError:
        print(f"--- ERRO: Arquivo de áudio não encontrado em '{caminho_arquivo}' ---")
        return None
    except Exception as e:
        print(f"--- ERRO DURANTE A TRANSCRIÇÃO ---")
        print(f"Erro: {e}")
        print("Verifique se o ffmpeg está instalado e no PATH do sistema.")
        return None
# --- FIM DA NOVA FUNÇÃO ---


def main():
    print("Iniciando o Chat RAG (Assistente com Áudio)...")

    # --- 1. Carregar Componentes (igual) ---
    print(f"Carregando modelo de embeddings local: {EMBEDDING_MODEL_NAME}")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'}
    )
    print(f"Carregando VectorDB de: {PATH_VECTOR_DB}")
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
    
    # --- 2. Criar a Cadeia RAG Simples (RetrievalQA) ---
    print("Criando a cadeia RAG (RetrievalQA)...")
    rag_prompt = PromptTemplate(
        template=RAG_TEMPLATE, 
        input_variables=["context", "question"]
    )
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": rag_prompt}
    )

    # --- 3. Memória Manual e Estado (igual) ---
    chat_history = []
    conversation_state = "START" 
    solicitacao_cliente_original = "" 
    
    print("\n--- Assistente de Requisitos Pronto! ---")
    print("Para começar, cole o texto da entrevista OU o caminho para um arquivo de áudio (ex: C:\\caminho\\audio.mp3).")
    print("Digite 'novo' para recomeçar ou 'sair'.")

    while True:
        pergunta_usuario = ""
        texto_da_entrevista = "" # <- NOVO: Guarda o texto final (digitado ou transcrito)
        
        # --- Lógica de Estado ATUALIZADA ---
        if conversation_state == "START":
            entrada_usuario = input("\nEntrevista (texto ou caminho do arquivo de áudio): ")
            
            if entrada_usuario.lower() == 'sair':
                break
            if entrada_usuario.lower() == 'novo': # Permite 'novo' já no início
                chat_history = []
                solicitacao_cliente_original = ""
                print("\n--- Certo! Limpando a sessão. ---")
                continue

            # VERIFICA SE É UM ARQUIVO DE ÁUDIO
            # Heurística simples: termina com extensões comuns E existe o arquivo?
            if any(entrada_usuario.lower().endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.ogg', '.flac']) and os.path.exists(entrada_usuario):
                # É um caminho de áudio, transcreve!
                texto_transcrito = transcrever_audio_com_whisper(entrada_usuario)
                if texto_transcrito is None: # Erro na transcrição
                    continue # Volta e pede a entrada de novo
                texto_da_entrevista = texto_transcrito
            else:
                # Assume que é texto digitado
                texto_da_entrevista = entrada_usuario

            # Prepara a pergunta para a cadeia RAG
            pergunta_para_chain = PROMPT_ANALISTA_OCULTO.format(
                solicitacao_cliente=texto_da_entrevista
            )
            chat_history = []
            solicitacao_cliente_original = texto_da_entrevista # Salva o texto (original ou transcrito)
            conversation_state = "REFINING" 
            print("\nAnalisando solicitação e gerando requisitos...")

        elif conversation_state == "REFINING":
            # (Lógica de refinamento, 'aprovado', 'novo', 'sair' como antes)
            pergunta_usuario = input("\nVocê (refine, 'aprovado' para enviar ao Jira, 'novo', 'sair'): ")

            if pergunta_usuario.lower() == 'sair': break
            if pergunta_usuario.lower() == 'novo':
                conversation_state = "START"; chat_history = []; solicitacao_cliente_original = ""
                print("\n--- Certo! Limpando a sessão. ---"); continue
            
            if pergunta_usuario.lower() == 'aprovado':
                # (Lógica de aprovação e loop para criar stories como antes)
                if not chat_history: print("Nada para aprovar."); continue
                print("\nAprovando e quebrando requisitos para o Jira...")
                requisitos_aprovados = chat_history[-1][1] 
                lista_de_requisitos = requisitos_aprovados.split("---[NOVO REQUISITO]---")
                print(f"Encontrados {len(lista_de_requisitos)} requisitos para criar...")
                total_criados = 0
                for req in lista_de_requisitos:
                    if req.strip():
                        key = criar_story_no_jira(req.strip(), solicitacao_cliente_original)
                        if key: total_criados += 1
                print(f"\n--- Concluído! {total_criados} tickets criados no Jira. ---")
                continue

            # É um refinamento
            print("\nRefinando com base no histórico...")
            historico_formatado = "\n".join([f"{item[0]}: {item[1]}" for item in chat_history])
            pergunta_para_chain = f"Histórico:\n---\n{historico_formatado}\n---\nRefinamento: {pergunta_usuario}"
        # --- Fim da Lógica de Estado ---

        # Envia a pergunta para a cadeia
        try:
            resposta = qa_chain.invoke({"query": pergunta_para_chain})
            resultado_assistente = resposta["result"]
            
            print("\n--- Assistente ---")
            print(resultado_assistente)
            
            # Salva na memória manual (salva a pergunta original do usuário, não a formatada)
            # Se for a primeira vez, salva o texto_da_entrevista
            pergunta_salvar = texto_da_entrevista if conversation_state == "REFINING" and not chat_history else pergunta_usuario
            chat_history.append( ("Você", pergunta_salvar) )
            chat_history.append( ("Assistente", resultado_assistente) )
            
        except Exception as e:
            print(f"--- ERRO AO PROCESSAR A SOLICITAÇÃO ---")
            print(f"Erro: {e}")
            # Considerar resetar o estado ou dar mais informações
            # conversation_state = "START" # Opcional: força recomeçar em caso de erro

if __name__ == "__main__":
    main()