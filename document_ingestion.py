import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings 
from config import cfg 

# Initialize embeddings once
embeddings_model = HuggingFaceEmbeddings(
    model_name=cfg.EMBEDDING_MODEL
)

def get_vector_store() -> Chroma:
    """
    Returns the persistent Chroma vector store.
    """
    return Chroma(
        persist_directory=cfg.VECTOR_STORE_PATH,
        embedding_function=embeddings_model
    )

def ingest_document(file_path: str):
    print(f"Ingesting document: {file_path}")
    
    try:
        # 1. Load Document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        if not documents:
            print("No content found in PDF.")
            return

        # 2. Split into Chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200
        )
        doc_chunks = text_splitter.split_documents(documents)
        
        if not doc_chunks:
            print("No text chunks created.")
            return

        print(f"Document split into {len(doc_chunks)} chunks.")
        
        # 3. Connect to DB
        vector_store = get_vector_store()

        # 4. SAFE RESET: Delete existing IDs instead of deleting the folder
        # This prevents the "readonly database" error by keeping the file open/valid
        try:
            existing_data = vector_store.get()
            if existing_data and 'ids' in existing_data:
                existing_ids = existing_data['ids']
                if existing_ids:
                    print(f"Clearing {len(existing_ids)} existing chunks from DB...")
                    # Delete in batches to be safe, though Chroma handles large lists well
                    vector_store.delete(ids=existing_ids)
                    print("Previous document data cleared.")
        except Exception as e:
            print(f"Warning during DB clear: {e}")

        # 5. Add new documents
        vector_store.add_documents(doc_chunks)
        print("Document added to persistent Chroma store.")

    except Exception as e:
        print(f"Error during ingestion: {e}")
        raise e

def search_internal_documents(query: str) -> list[str]:
    try:
        print(f"Searching internal docs for: {query}")
        vector_store = get_vector_store()
        results = vector_store.similarity_search(query, k=3)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"Error during internal search: {e}")
        return []