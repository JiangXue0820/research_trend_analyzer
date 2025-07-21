# llm_provider.py
"""
Utility to initialize the language model (LLM) based on configuration.
Supports local models and API-based models (OpenAI, DeepSeek, Gemma).
"""
import config

# Import LangChain LLM classes
from langchain.chat_models import ChatOpenAI
try:
    # DeepSeek integration (requires langchain-deepseek installed)
    from langchain_deepseek import ChatDeepSeek
except ImportError:
    ChatDeepSeek = None
# Gemini via Google AI Studio (Gemini API)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

from langchain.llms import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModel, pipeline
from langchain.callbacks.manager import CallbackManager
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Initialize a global Langfuse client and handler
langfuse_client = Langfuse(
    public_key=config.LANGFUSE_PUBLIC_KEY,
    secret_key=config.LANGFUSE_SECRET_KEY,
    host=config.LANGFUSE_HOST
)
langfuse_handler = CallbackHandler(tracer=langfuse_client)

def get_llm():
    """Initialize and return an LLM instance based on config settings."""
    # 1. Use a local model if specified
    if config.USE_LOCAL_LLM or config.LLM_PROVIDER.lower() == "local":
        model_path = config.LOCAL_MODEL_PATH        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModel.from_pretrained(model_path)
        generation_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
        llm = HuggingFacePipeline(pipeline=generation_pipeline)
        llm.callback_manager = CallbackManager([langfuse_handler])
        llm.verbose = True
        return llm

    # 2. API-based models
    provider = config.LLM_PROVIDER.lower()
    if provider == "openai":
        # OpenAI chat model (requires OPENAI_API_KEY)
        return ChatOpenAI(model_name=config.OPENAI_MODEL, 
                          openai_api_key=config.OPENAI_API_KEY,
                          callback_manager=CallbackManager([langfuse_handler]),
                          verbose=True)
    elif provider == "deepseek" and ChatDeepSeek:
        # DeepSeek API model
        return ChatDeepSeek(model=config.DEEPSEEK_MODEL, 
                            api_key=config.DEEPSEEK_API_KEY,
                            callback_manager=CallbackManager([langfuse_handler]),
                            verbose=True)
    elif provider == "gemini" and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            api_key=config.GOOGLE_API_KEY,
            callback_manager=CallbackManager([langfuse_handler]),
            verbose=True
        )
    else:
        # Fallback to OpenAI as default
        return ChatOpenAI(model_name=config.OPENAI_MODEL, openai_api_key=config.OPENAI_API_KEY)
