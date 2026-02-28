try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import os
import time
import zipfile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage

if not os.path.exists("endfield_db"):
    with zipfile.ZipFile("endfield_db.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
        
# --- CONFIGURATION ---
# Set the API key so LangChain can find it automatically
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

# --- SETUP RAG PIPELINE (CACHED) ---
# We use @st.cache_resource so the database and AI only load ONCE when the app starts.
@st.cache_resource
def setup_rag_pipeline():
    # 1. Load the Local Knowledge Base
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 2. Connect to ChromaDB
    db = Chroma(persist_directory="./endfield_db", embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 10})

    # 3. Setup the AI Model
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    # 4. Define the System Instructions
    # Contextualize Question Prompt (Translates "it" to the actual subject)
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # Create the memory-enabled database searcher
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    system_prompt = (
        "You are an Arknights: Endfield logistics expert. "
        "Use the following pieces of retrieved context to answer the user's question. "
        "Maintain a professional, helpful tone. If you don't know, say so."
        "\n\n"
        "{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # 5. Create the Retrieval Chain
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain

# Initialize the pipeline
rag_chain = setup_rag_pipeline()

st.set_page_config(page_title="Endfield_Bot", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
    }

    .block-container {
        padding-top: 3rem !important;
    }
    
    .stChatInputContainer {
        border: 1px solid #F2C100; 
        box-shadow: 0 0 10px rgba(242, 193, 0, 0.2);
    }
    
    [data-testid="stChatInputSubmitButton"]:disabled {
        background-color: transparent !important;
    }
    [data-testid="stChatInputSubmitButton"]:disabled svg {
        fill: rgba(226, 232, 240, 0.5) !important;
    }

    [data-testid="stChatInputSubmitButton"]:not(:disabled) {
        background-color: #FFFF33 !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }
    [data-testid="stChatInputSubmitButton"]:not(:disabled) svg {
        fill: #000000 !important;
        color: #000000 !important;
    }
            
    [data-testid="stVerticalBlock"] {
        position: relative;
    }
    
    .block-container::before {
        content: "";
        position: absolute;
        top: 0;
        right: 3%;
        width: 45px;
        height: 140px;
        background-color: #FFFF33;
        z-index: 1;
        box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
    }
            
    </style>
""", unsafe_allow_html=True)

# --- STREAMLIT UI ---
with st.sidebar:
    st.image("https://endfield.gg/wp-content/uploads/sites/38/2024/03/Arknights-Endfield-Logo.webp", use_container_width=True)
    st.divider()
    st.markdown("Welcome, Operator. You are connected to the comprehensive Talos-II master database.")
    st.markdown("Ask me about Operator profiles, factory blueprints, combat mechanics, or planetary lore.")
    
st.markdown(
    """
    <div style='border-bottom: 1px solid #1A1E26; padding-bottom: 10px; margin-bottom: 20px;'>
        <h2 style='color: #E2E8F0; margin-bottom: 0; padding-bottom: 0; font-style: italic; font-weight: 800;'>EALA</h2>
        <p style='color: rgba(226, 232, 240, 0.6); font-size: 14px; margin-top: 5px;'>Ask me anything about Arknights: Endfield</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Setup Memory for the Webpage
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the Chat History on the Screen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if user_question := st.chat_input("Operator, what is your question?"):
    
    # Translate Streamlit history into LangChain format BEFORE adding the new question
    langchain_history = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            langchain_history.append(HumanMessage(content=msg["content"]))
        else:
            langchain_history.append(AIMessage(content=msg["content"]))

    # Show the user's question and save it visually
    with st.chat_message("user"):
        st.markdown(user_question)
    st.session_state.messages.append({"role": "user", "content": user_question})

    # The Bot's Turn to Answer
    with st.chat_message("assistant"):
        with st.spinner("Routing query through Perlica's terminal..."):
            try:

                start_time = time.time()
                # Pass BOTH the question and the memory to LangChain
                response = rag_chain.invoke({
                    "input": user_question,
                    "chat_history": langchain_history
                })
                bot_response = response['answer']

                end_time = time.time()
                
                st.markdown(bot_response)
                execution_time = end_time - start_time
                st.caption(f"Response generated in {execution_time:.2f} seconds")

                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
            except Exception as e:
                st.error(f"Connection Error: {e}")