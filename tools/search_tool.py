# search_tool.py
from langchain.utilities import SerpAPIWrapper
from retriever.vector_store import ResearchPaperStore
import config

# Initialize the research paper store (this will be set in main)
paper_store = None

def init_paper_store(store: ResearchPaperStore):
    """Initialize the global paper store instance (to be called in main after data is loaded)."""
    global paper_store
    paper_store = store

def search_local_papers(query: str):
    """Search the local research paper database for relevant papers."""
    if paper_store is None:
        return "Paper database is not initialized."
    # Perform similarity search in the vector store
    results = paper_store.similarity_search(query, top_k=3)
    if not results:
        return "No relevant papers found in the database."
    # Format the top results (title, conference, year, snippet of abstract)
    summaries = []
    for doc in results:
        title = doc.metadata.get('title', 'Unknown Title')
        conf = doc.metadata.get('conference', '')
        year = doc.metadata.get('year', '')
        snippet = ""
        if 'abstract' in doc.metadata:
            snippet = doc.metadata['abstract'][:100]  # first 100 characters of abstract
            if len(doc.metadata['abstract']) > 100:
                snippet += '...'
        summaries.append(f"- {title} ({conf} {year}): {snippet}")
    return "\n".join(summaries)

def web_search(query: str):
    """Search the web for information related to the query."""
    if config.SERPAPI_API_KEY:
        # Use SerpAPI to perform a web search
        search = SerpAPIWrapper(serpapi_api_key=config.SERPAPI_API_KEY)
        result = search.run(query)
        return result
    else:
        return "Web search API key not provided. Unable to perform web search."
