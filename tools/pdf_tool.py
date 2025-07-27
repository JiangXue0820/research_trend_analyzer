# pdf_tool.py
import os
from loaders import pdf_loader
from loaders import paper_crawler
from configs import llm_provider
from langchain.docstore.document import Document

# Optionally, use a shared paper_store if needed (set via init_paper_store similar to search_tool)
paper_store = None
def init_paper_store(store):
    """Initialize paper store for pdf tool (to find PDF by title)."""
    global paper_store
    paper_store = store

def load_and_summarize_paper(input_str: str):
    """Load a research paper (by URL, local path or title) and return a summary."""
    pdf_path = None
    # Determine if input is a URL
    if input_str.lower().startswith("http"):
        pdf_path = paper_crawler.download_pdf(input_str)
    elif input_str.lower().endswith(".pdf") and os.path.exists(input_str):
        # If input is a local PDF file path
        pdf_path = input_str
    else:
        # If input is not a path or URL, treat it as a title/query to find in the local database
        if paper_store:
            results = paper_store.similarity_search(input_str, top_k=1)
            if results:
                pdf_path = results[0].metadata.get('pdf_path')
    if not pdf_path:
        return f"Error: Unable to find a PDF for '{input_str}'. Please provide a valid URL or title."
    # Extract text from the PDF
    text = pdf_loader.extract_text(pdf_path)
    if not text:
        return "Error: Failed to extract text from the PDF."
    # Prepare documents for summarization (split text into chunks to avoid context length issues)
    chunk_size = 3000
    docs = [Document(page_content=text[i:i+chunk_size]) for i in range(0, len(text), chunk_size)]
    # Summarize using an LLM chain (map-reduce summarization)
    llm = llm_provider.get_llm()
    from chains import paper_summary_chain
    summary = paper_summary_chain.summarize_documents(llm, docs)
    return summary.strip()
