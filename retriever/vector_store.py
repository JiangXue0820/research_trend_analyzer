# vector_store.py
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
import config

class ResearchPaperStore:
    """Manages the Chroma vector store for research paper embeddings."""
    def __init__(self):
        # Initialize embedding model: use OpenAI embeddings if API key provided, otherwise use HuggingFace
        if config.OPENAI_API_KEY:
            self.embedding = OpenAIEmbeddings(openai_api_key=config.OPENAI_API_KEY)
        else:
            self.embedding = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL_NAME)
        # Initialize Chroma vector database (with persistence)
        self.chroma = Chroma(collection_name="papers", persist_directory=config.PERSIST_DIR, embedding_function=self.embedding)
    
    def index_papers(self, documents):
        """Add a list of Document objects (with metadata) to the vector store."""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        # Add texts and metadata to Chroma index
        self.chroma.add_texts(texts=texts, metadatas=metadatas)
        self.chroma.persist()  # Save data to disk
    
    def similarity_search(self, query, top_k=5):
        """Find similar documents in the store for a given query text."""
        return self.chroma.similarity_search(query, k=top_k)
    
    def similarity_search_with_filter(self, query, filter_metadata, top_k=5):
        """Find similar documents with a metadata filter (e.g., by conference or year)."""
        return self.chroma.similarity_search(query, k=top_k, filter=filter_metadata)
