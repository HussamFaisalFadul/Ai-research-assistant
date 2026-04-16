import os
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from .config import CHROMA_DB_PATH

_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        print("⚡ Loading embedding model...")
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _embeddings


def init_vector_store():
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    get_embeddings()
    print("✅ Vector store initialized")


def get_vector_store():
    return Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=get_embeddings(),
        collection_name="research_docs_v3"
    )


def get_documents_count():
    try:
        vs = get_vector_store()
        return vs._collection.count()
    except:
        return 0


def add_documents_to_vectorstore(file_path: str):
    print(f"📄 Processing: {file_path}")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    print(f"📄 Found {len(documents)} pages")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    splits = text_splitter.split_documents(documents)
    print(f"✂️ Created {len(splits)} chunks")

    vectorstore = get_vector_store()
    vectorstore.add_documents(splits)
    print("✅ Indexed successfully")
    return len(splits)
