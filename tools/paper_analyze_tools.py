import os
import sys
sys.path.append("../")
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from functools import partial
import logging
import sqlite3
from langchain.tools import StructuredTool
from langchain.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from configs import config, llm_provider
from utils import prompts, paper_crawler, data_process
from tools.paper_fetch_tools_sql import load_paper_by_title

# ----------- 1. Define PaperMetaModel and meta construction function -----------

class PaperMetaModel(BaseModel):
    title: str = Field(..., description="Title of the paper")
    authors: str = Field(..., description="Authors of the paper")
    conference: str = Field(..., description="Publication conference")
    year: str = Field(..., description="Publication year")
    paper_url: str = Field(..., description="url for downloading the paper")

def construct_paper_meta(
    title: str,
) -> dict:
    load_result = load_paper_by_title(title)
    if "error" not in load_result.keys() and len(load_result['papers'])==1:
        paper_info_dict = load_result['papers'][0]
    else:
        return {"error": f"{load_result['error']}"}

    meta = {k: paper_info_dict.get(k) for k in ["title", "authors", "conference", "year", "paper_url"]}
    return {
        "message": "metadata for paper {} constructed",
        "meta": meta
    }

# ----------- 2. Tool: Download & Parse & Vectorize Paper -----------


class ParseAndSavePDFArgs(BaseModel):
    title: str = Field(..., description="Title of the paper")

def fetch_and_parse_pdf(
    title: str,
    embedding_fn,
    text_splitter,
    vector_db_path: str,
    paper_path: str
) -> dict:
    """
    Download a PDF from er_url in paper_meta, parse, split, embed, and save chunks to a vector DB.
    Returns: {"chunks_added": N, "vector_db_path": ...} or {"error": ...}
    """
    result = construct_paper_meta(title)
    if "error" not in result.keys and "meta" in result.keys():
        paper_meta = result['meta']
    else:                  
        return {"error": f"fail to construct metadata for paper {title}: {result['error']}"}         
                                                     
    pdf_url = paper_meta.get("paper_url")
    if not pdf_url:
        return {"error": f"paper info does not contain paper_url: {paper_meta}"}
    
    # Download PDF
    resp = paper_crawler.download_pdf(pdf_url, save_path=paper_path)
    if resp != 'succeed':
        return {"error": resp}

    # Load and split PDF
    docs = PyMuPDFLoader(paper_path).load()
    split_chunks = text_splitter.split_documents(docs)

    # Attach metadata
    parsed_chunks = []
    for idx, chunk in enumerate(split_chunks):
        paper_meta["chunck_id"] = idx
        parsed_chunks.append(Document(page_content=chunk.page_content, metadata=paper_meta))

    # Save to vectorstore
    if os.path.exists(vector_db_path):
        vectorstore = FAISS.load_local(vector_db_path, embedding_fn)
        vectorstore.add_documents(parsed_chunks)
    else:
        vectorstore = FAISS.from_documents(parsed_chunks, embedding_fn)
    
    vectorstore.save_local(vector_db_path)
    return {
        "message": f"fetched pdf for paper {title} and saved to vector store {vector_db_path}", 
        "paper": title, "chunks_added": len(parsed_chunks), "vector_db_path": vector_db_path
        }

# Tool construction
fetch_and_parse_pdf_tool = StructuredTool.from_function(
    func=partial(
        fetch_and_parse_pdf, 
        embedding_fn=llm_provider.get_embedding_model(config), 
        text_splitter=llm_provider.get_text_splitter(config), 
        vector_db_path=config.VECTOR_DB_PATH,
        paper_path=config.TEMP_PAPER_PATH
    ),
    args_schema=ParseAndSavePDFArgs,
    name="parse_and_save_pdf",
    description="Given a PDF paper title, download, parse, split, embed and save to vector DB for RAG retrieval."
)


# ----------- 3. Tool: RAG Retriever -----------
class RagRetrieveArgs(BaseModel):
    question: str = Field(..., description="Your question about the paper")
    title: str = Field(..., description="Metadata about the paper for filtering")

def rag_retrieve(
    question: str,
    title: str,
    vector_db_path: str,
    rag_config: Dict,
    embedding_fn,
) -> Dict[str, Any]:
    
    if not os.path.exists(vector_db_path):
        logging.error(f"Vectorstore not found at {vector_db_path}")
        return {"error": f"Vectorstore not found at {vector_db_path}"}
    vectorstore = FAISS.load_local(vector_db_path, embedding_fn)

    # Construct paper_meta dict from paper_info (exclude None or empty)
    result = construct_paper_meta(title)
    if "error" not in result.keys and "meta" in result.keys():
        paper_meta = result['meta']
    else:                  
        return {"error": f"fail to construct metadata for paper {title}: {result['error']}"} 
    
    # Only filter if something present
    retriever_config = rag_config.copy()
    if paper_meta:
        retriever_config = retriever_config.copy()
        retriever_config.setdefault("search_kwargs", {})
        retriever_config["search_kwargs"]["filter"] = paper_meta

    retriever = vectorstore.as_retriever(**retriever_config)
    docs = retriever.get_relevant_documents(question)
    logging.info(f"Retrieved {len(docs)} docs for question: {question} with filter: {paper_meta}")
    return {
        "message": f"Retrieved {len(docs)} docs for question: {question} with filter: {paper_meta}",
        "docs": docs
        }


rag_retrieve_tool = StructuredTool.from_function(
    func=partial(
        rag_retrieve,
        vector_db_path=config.VECTOR_DB_PATH,
        rag_config=config.RAG_RETRIEVER_CONFIG,
        embedding_fn=llm_provider.get_embedding_model(config),
    ),
    args_schema=RagRetrieveArgs,
    name="rag_retrieve",
    description="Retrieve relevant document chunks for a question, filtering by paper title."
)


# ----------- 3. Tool: RAG Q&A -----------
class RagQAToolArgs(BaseModel):
    question: str = Field(..., description="Question about the paper")
    title: str = Field(..., description="Metadata about the paper for filtering")
    context: str = Field(..., description="Relevant chunks from the retriever tool")

def rag_qa(
        question: str,
        title: str, 
        context: str, 
        llm) -> str:
    
    result = construct_paper_meta(title)
    if "error" not in result.keys and "meta" in result.keys():
        paper_meta = result['meta']
    else:                  
        return {"error": f"fail to construct metadata for paper {title}: {result['error']}"} 
       
    prompt = f"""Given the following paper context and metadata, answer the question thoroughly.

Paper Context:
{paper_meta}
{context}

Question: {question}
Answer:"""
    try:
        response = llm.invoke(prompt)
        logging.info("[RAG] LLM generated an answer successfully.")
        return {
            "message": "LLM generated an answer successfully.",
            "answer": response.content if hasattr(response, "content") else str(response)
        }
    
    except Exception as e:
        logging.exception("[RAG] Exception occurred while calling LLM.")
        return {"error": f"LLM service failed: {str(e)}"}

rag_qa_tool = StructuredTool.from_function(
    func=partial(rag_qa, llm=llm_provider.get_llm(config)),
    args_schema=RagQAToolArgs,
    name="rag_qa",
    description="Answer user questions about a paper given relevant context chunks."
)

# ----------- 4. Tool: Summarize Paper Insights -----------
class PaperSummaryArgs(BaseModel):
    title: str = Field(..., description="List of papers to be summarized")
    context: str = Field(..., description="Relevant chunks from the retriever tool")

def summarize_paper(
    title: str,
    context: str, 
    instruction: str, 
    llm,
    summary_path: str) -> str:

    # Construct paper_meta dict from paper_info (exclude None or empty)
    result = construct_paper_meta(title)
    if "error" not in result.keys and "meta" in result.keys():
        paper_meta = result['meta']
    else:                  
        return {"error": f"fail to construct metadata for paper {title}: {result['error']}"} 
    
    prompt = f"""{instruction}

**Paper Context**
{paper_meta}
{context}

**Summary**
"""
    
    try:
        response = llm.invoke(prompt)
        logging.info("[SUM] LLM generated a summary successfully.")
        answer = response.content if hasattr(response, "content") else str(response)

        paper_summary_path = os.path.join(summary_path, f"{paper_meta["title"].lower()}.md")
        data_process.save_md_file(answer, paper_summary_path)

        return {
            "message": f"LLM generated an answer successfully, saved to {paper_summary_path}",
            "answer": answer
        }
    except Exception as e:
        logging.exception("[SUM] Exception occurred while calling LLM.")
        return {"error": f"LLM service failed: {str(e)}"}

summarize_paper_tool = StructuredTool.from_function(
    func=partial(
        summarize_paper, 
        instruction=prompts.paper_summarization_prompt, 
        llm=llm_provider.get_llm(config),
        summary_path=config.PAPER_SUMMARY_PATH
    ),
    args_schema=PaperSummaryArgs,
    name="summarize_paper",
    description="Given one paper title, Write and save a summary of this paper to a specific instruction or template, including motivation, methodology, experiment results, etc."
)

# ----------- 5. Tool: Summarize Research Trend -----------
class TrendSummaryArgs(BaseModel):
    conference: str = Field(..., description="Conference name (e.g., NeurIPS)")
    year: int = Field(..., description="Year")
    topic: str = Field(..., description="Research topic (e.g., privacy, LLM)")

def summarize_research_trend(
    conference: str,
    year: int,
    topic: str,
    paper_db_path: str,
    llm,
    highlight_instruction: str,
    trend_instruction: str,
    summary_path: str,
    trend_path: str
) -> dict:
    """
    Summarizes research trend for a topic in a conference and year.
    """
    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, abstract FROM papers WHERE conference=? AND year=? AND topic=?",
            (conference, year, topic),
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"error": f"No papers found in database for {conference} {year} topic '{topic}'."}
        
        paper_titles = [row[0] for row in rows]
        summary_paths = [os.path.join(summary_path, f"{title.lower()}.md") for title in paper_titles]

        # Check if all summaries exist
        missing = [t for t, s in zip(paper_titles, summary_paths) if not s or not os.path.exists(s)]
        if missing:
            return {"error": f"Missing summary markdown for paper(s): {missing}"}

        # Compose highlights
        highlight_list = []
        for title, md_path in zip(paper_titles, summary_paths):
            paper_summary = data_process.load_md_file(md_path)  # get full text, or use a section
            if "error" in paper_summary:
                return {"error": f"Error loading summary for '{title}': {paper_summary['error']}"}
            
            paper_highlight = data_process.get_md_section(paper_summary, section_name = "6. Highlights")

            if "error" in paper_highlight: 
                # Use LLM to write a highlight for this paper
                highlight_prompt = (
                    f"{highlight_instruction}\n\n"
                    f"Title: {title}\n"
                    f"Summary: {paper_summary}\n"
                    f"Please generate a concise highlight paragraph (problem, contribution, method)."
                    )
                try:
                    resp = llm.invoke(highlight_prompt)
                    paper_highlight = resp.content if hasattr(resp, "content") else str(resp)
                except Exception as e:
                    return {"error": f"LLM failed on highlight for '{title}': {e}"}
                
            highlight_list.append(f"- **{title}**: {paper_highlight.strip()}")

        all_highlights = "\n\n".join(highlight_list)
        
        # LLM trend summary
        trend_prompt = (
            f"{trend_instruction}\n\n"
            f"Here are the highlights of all papers on topic '{topic}' at {conference} {year}:\n\n"
            f"{all_highlights}\n\n"
            f"Write a summary paragraph capturing the main trends, open challenges, and directions."
        )
        try:
            resp = llm.invoke(trend_prompt)
            trend_summary = resp.content if hasattr(resp, "content") else str(resp)
        except Exception as e:
            return {"error": f"LLM failed on trend summary: {e}"}

        # Save to markdown
        os.makedirs(trend_path, exist_ok=True)
        fname = f"{conference}_{year}_{topic.replace(' ', '_')}.md"
        md_path = os.path.join(trend_path, fname)
        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Research Trend: {conference} {year} - {topic}\n\n")
                f.write("## Paper Highlights\n\n")
                f.write(all_highlights)
                f.write("\n\n## Trend Summary\n\n")
                f.write(trend_summary.strip())
        except Exception as e:
            return {"error": f"Failed to save trend summary: {e}"}

        return {
            "success": True,
            "trend_summary_path": md_path,
            "trend_summary": trend_summary,
        }
    except Exception as e:
        return {"error": f"Exception in trend summary: {e}"}

trend_summary_tool = StructuredTool.from_function(
    func=partial(
        summarize_research_trend,
        paper_db_path=config.PAPER_DB_PATH,
        highlight_instruction=prompts.paper_highlight_prompt,
        trend_instruction=prompts.trend_summarize_prompt,
        llm=llm_provider.get_llm(config),
        summary_path=config.PAPER_SUMMARY_PATH,
        trend_path=config.TREND_SUMMARY_PATH),

    args_schema=TrendSummaryArgs,
    name="summarize_research_trend",
    description="Summarize the research trend of a topic in a conference and year by synthesizing the highlights of all related papers."
)
# ----------- 5. Compose Toolkit -----------
paper_analyze_toolkit = [
    fetch_and_parse_pdf_tool,
    rag_qa_tool,
    summarize_paper_tool,
    trend_summary_tool
]
