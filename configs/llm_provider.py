# llm_provider.py
"""
Utility to initialize the language model (LLM) based on configuration.
Supports local models and API-based models (OpenAI, DeepSeek, Gemma).
"""
# Import LangChain LLM classes
from langchain_community.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings

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

from langchain_community.llms import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModel, pipeline
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Initialize a global Langfuse client and handler


def get_llm(config):
    """Initialize and return an LLM instance based on config settings."""
    langfuse = get_client(public_key=config.LANGFUSE_API_KEY_PUBLIC)
    langfuse_handler = CallbackHandler()

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
                          callback_manager=CallbackManager([StreamingStdOutCallbackHandler(), langfuse_handler]),
                          verbose=True)
    elif provider == "deepseek" and ChatDeepSeek:
        # DeepSeek API model
        return ChatDeepSeek(model=config.DEEPSEEK_MODEL, 
                            api_key=config.DEEPSEEK_API_KEY,
                            callback_manager=CallbackManager([StreamingStdOutCallbackHandler(), langfuse_handler]),
                            verbose=True)
    elif provider == "gemini" and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=config.GOOGLE_MODEL,
            api_key=config.GOOGLE_API_KEY,
            callback_manager=CallbackManager([StreamingStdOutCallbackHandler(), langfuse_handler]),
            verbose=True
        )
    else:
        # Fallback to OpenAI as default
        return ChatOpenAI(model_name=config.OPENAI_MODEL, openai_api_key=config.OPENAI_API_KEY)


def get_embedding_model(config):
    # 1. Use a local model if specified
    if config.USE_LOCAL_EMBEDDING or config.EMBEDDING_PROVIDER.lower() == "local":
        model_name = "BAAI/bge-m3"
        return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu",
                              "trust_remote_code": True}, # 可改为 "cuda" 用GPU
        )

    # 2. API-based models
    provider = config.EMBEDDING_PROVIDER.lower()
    if provider == 'openai':
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=config.OPENAI_API_KEY,
                                )
    elif provider == "gemini":
        return GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            api_key=config.GOOGLE_API_KEY,
            )
    else:
        print("Currently only support gemini as provier")
        return None
    
def get_text_splitter(config):
    return RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)

