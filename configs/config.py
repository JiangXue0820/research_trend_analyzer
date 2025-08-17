# config.py
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration for model selection and API keys
USE_LOCAL_LLM = False  # Set True to use a local LLM instead of an API-based model
LLM_PROVIDER = "gemini"  # Options: "openai", "deepseek", "gemini", "local"

# Configuration for RAG
USE_LOCAL_EMBEDDING = True
EMBEDDING_PROVIDER = "local"  # Options: "openai", "deepseek", "gemini", "local" sentence-transformers--all-MiniLM-L6-v2
# EMBEDDING_MODEL_NAME = "BAAI/bge-m3"  # HuggingFace model for embeddings
EMBEDDING_MODEL_NAME = "sentence-transformers--all-MiniLM-L6-v2"  # HuggingFace model for embeddings

# API Keys and model identifiers
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-3.5-turbo"  # OpenAI model to use for the assistant

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"  # Example DeepSeek model name

# If using Gemini (Google's open model) via local deployment (e.g., Ollama)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = "gemini-2.5-flash"  # Example model name for Gemma 

# Local model configuration (for ChatGLM, Qwen, etc.)
LOCAL_MODEL_PATH = "models/chatglm-6b"  # Path or name for local HuggingFace model
LOCAL_MODEL_TYPE = "chatglm"          # Type of local model ("chatglm", "qwen", etc.)

# Langfuse observability
LANGFUSE_API_KEY_SECRET = os.getenv("LANGFUSE_API_KEY_SECRET", "")
LANGFUSE_API_KEY_PUBLIC = os.getenv("LANGFUSE_API_KEY_PUBLIC", "")
LANGFUSE_PROJECT_NAME = os.getenv("LANGFUSE_PROJECT_NAME", "research_agent")
LANGFUSE_HOST="https://cloud.langfuse.com"

# Configuration for paper paths
PAPER_ROOT_PATH = "papers"
VECTOR_DB_PATH = os.path.join(PAPER_ROOT_PATH, "vector_db")  # Directory to save vector db

PAPER_DB_PATH = os.path.join(PAPER_ROOT_PATH, "papers.db")  # Directory to save downloaded PDFs
PAPER_LIST_PATH = os.path.join(PAPER_ROOT_PATH, "paper_list")  # Directory to save downloaded PDFs
PAPER_SUMMARY_PATH = os.path.join(PAPER_ROOT_PATH, "paper_summary")  # Directory to save summary of each paper
TREND_SUMMARY_PATH = os.path.join(PAPER_ROOT_PATH, "trend_summary")  # Directory to save research trend
TEMP_PAPER_PATH = os.path.join(PAPER_ROOT_PATH, "temp.pdf")  # Directory to save downloaded PDFs

# Configuration for text splitter 
CHUNK_SIZE = 700
CHUNK_OVERLAP = 150
MAX_TEXT_LENGTH=50000


RAG_RETRIEVER_CONFIG = {
    "search_type": "similarity",    # 可选："similarity", "mmr"
    # "search_kwargs": {
    #     "k": 5,                    # 检索返回最相关 top k
        # "fetch_k": 20,          # mmr 时可加 fetch_k 参数
        # "lambda_mult": 0.5      # mmr 时可加 lambda_mult
    # }
}
