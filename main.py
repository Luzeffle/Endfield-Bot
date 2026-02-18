import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# --- CONFIGURATION ---
# Replace with your actual API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyBh6kEEraCcxJ7OYxoFrz0Vob4bgMKVZPY"

def start_chat():
    print("--- Initializing Endfield Logistics (Gemini 2.5) ---")
    
    # 1. Load the Local Knowledge Base
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    if not os.path.exists("./endfield_db"):
        print("❌ ERROR: Database not found. Run 'py ingest.py' first.")
        return

    db = Chroma(persist_directory="./endfield_db", embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 10})

    # 2. Setup the AI (Using your verified model name)
    llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", temperature=0.1)

    # 3. Define the System Instructions
    system_prompt = (
        "You are an Arknights: Endfield logistics expert. "
        "Use the following pieces of retrieved context to answer the user's question. "
        "Maintain a professional, helpful tone. If you don't know, say so."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # 4. Create the Retrieval Chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    print("\n✅ SYSTEM ONLINE. LOGISTICS OPERATOR READY.")
    print("(Type 'quit' or 'exit' to end the session)\n")
    
    while True:
        query = input("Operator, what is your query? > ")
        if query.lower() in ["quit", "exit"]:
            break
            
        try:
            # Query the system
            response = rag_chain.invoke({"input": query})
            print(f"\n🤖 AI: {response['answer']}\n")
            print("-" * 50)
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_chat()