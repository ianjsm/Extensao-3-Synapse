import os
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFDirectoryLoader,  # Carregador de PDF
    DirectoryLoader,       # Carregador de diretório genérico
    TextLoader             # Carregador de .txt
)
from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader # Carregador de .md
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

print("Carregando configurações...")
load_dotenv()

PATH_DOCUMENTOS = "documentos"
PATH_VECTOR_DB = "chroma_db"

def carregar_documentos(path):
    """
    Carrega todos os documentos (.pdf, .md, .txt) da pasta de documentos.
    """
    print("Carregando documentos de diferentes tipos...")
    
    # 1. Carregar PDFs
    loader_pdf = PyPDFDirectoryLoader(path, glob="**/*.pdf")
    docs_pdf = loader_pdf.load()
    print(f"Encontrados {len(docs_pdf)} documentos PDF.")

    # 2. Carregar Markdowns (.md)
    loader_md = DirectoryLoader(
        path,
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=True
    )
    docs_md = loader_md.load()
    print(f"Encontrados {len(docs_md)} documentos Markdown.")

    # 3. Carregar Textos (.txt)
    loader_txt = DirectoryLoader(
        path,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True
    )
    docs_txt = loader_txt.load()
    print(f"Encontrados {len(docs_txt)} documentos .txt.")

    # Combinar todas as listas de documentos
    return docs_pdf + docs_md + docs_txt

def main():
    print("Iniciando processo de ingestão...")

    # --- 1. Carregar Documentos (Load) ---
    documentos = carregar_documentos(PATH_DOCUMENTOS)
    
    if not documentos:
        print("Nenhum documento encontrado. Verifique a pasta 'documentos'.")
        return

    print(f"Total de {len(documentos)} documentos carregados de todas as fontes.")

    # --- 2. Dividir Documentos (Split) ---
    print("Dividindo documentos em 'chunks'...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documentos)
    print(f"Documentos divididos em {len(chunks)} chunks.")

    # --- 3. Criar Embeddings (Embed) ---
    print("Configurando modelo de embeddings...")
    embeddings_model = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    # --- 4. Armazenar Vetores (Store) ---
    print(f"Salvando embeddings no VectorDB em: {PATH_VECTOR_DB}")
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings_model,
        persist_directory=PATH_VECTOR_DB
    )

    print("--- Ingestão Concluída com Sucesso! ---")

if __name__ == "__main__":
    main()