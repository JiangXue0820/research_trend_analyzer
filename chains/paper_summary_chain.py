# paper_summary_chain.py
from langchain.chains.summarize import load_summarize_chain
from langchain.callbacks.manager import CallbackManager
from configs.llm_provider import langfuse_handler  

def summarize_documents(llm, documents):
    """Use a summarization chain to summarize a list of Document objects."""
    # Choose a map-reduce summarization chain for a comprehensive summary
    summarize_chain = load_summarize_chain(llm, chain_type="map_reduce", callback_manager=CallbackManager([langfuse_handler]), verbose=True)
    summary = summarize_chain.run(documents)
    return summary
