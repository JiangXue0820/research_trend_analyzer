# config.py
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration for model selection and API keys
USE_LOCAL_LLM = False  # Set True to use a local LLM instead of an API-based model
LLM_PROVIDER = "gemini"  # Options: "openai", "deepseek", "gemiin", "local"

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

# Vector store (Chroma) settings
PERSIST_DIR = "vector_store"  # Directory to persist the Chroma database
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # HuggingFace model for embeddings

# Other configurations
PAPER_DIR = "papers"  # Directory to save downloaded PDFs

# Langfuse observability
LANGFUSE_API_KEY_SECRET = os.getenv("LANGFUSE_API_KEY_SECRET", "")
LANGFUSE_API_KEY_PUBLIC = os.getenv("LANGFUSE_API_KEY_PUBLIC", "")
LANGFUSE_PROJECT_NAME = os.getenv("LANGFUSE_PROJECT_NAME", "research_agent")
LANGFUSE_HOST="https://cloud.langfuse.com"