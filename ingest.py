import os
import sys
# UPDATED IMPORTS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from langchain_huggingface import HuggingFaceEmbeddings # <--- NEW LOCAL TOOL
from langchain_community.vectorstores import Chroma

def create_vector_db():
    print("--- STARTING INGESTION (LOCAL MODE) ---")
    
    # 1. Load Data
    data_path = './data/wiki_crawl'
    if not os.path.exists(data_path):
        print(f"❌ ERROR: '{data_path}' not found. Did you run the crawler?")
        return

    print(f"Loading files from {data_path}...")
    loader = DirectoryLoader(
        data_path, 
        glob="**/*.txt", 
        loader_cls=TextLoader, 
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"✅ Found {len(documents)} files.")

    # 2. Split Text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    print(f"✅ Split into {len(texts)} chunks.")

    # 3. Create Database (USING LOCAL MODEL)
    print("Loading local model (all-MiniLM-L6-v2)... this downloads ~80MB once.")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print("Building database...")
    db = Chroma.from_documents(texts, embeddings, persist_directory="./endfield_db")
    print("✅ SUCCESS! Database saved locally.")

if __name__ == "__main__":
    create_vector_db()