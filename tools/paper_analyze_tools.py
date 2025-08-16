import os
import sys
sys.path.append("../")
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, AnyUrl
from functools import partial
import logging
import sqlite3
import pymupdf
from langchain.tools import StructuredTool
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from configs import config, llm_provider
from utils import prompts, paper_crawler, data_process, helper_func
from tools.paper_fetch_tools_sql import load_paper_by_title

# ----------- 1. Define PaperMetaModel and meta construction function -----------

# class PaperMetaModel(BaseModel):
#     title: str = Field(..., description="Title of the paper")
#     authors: List[str] = Field(default_factory=list, description="List of authors")
#     conference: str = Field(..., description="Publication conference")
#     year: int = Field(..., description="Publication year (4-digit)")
#     paper_url: AnyUrl = Field(..., description="URL for downloading the paper")
#     topic: List[str] = Field(default_factory=list, description="Topics the paper is related to")
#     keywords: List[str] = Field(default_factory=list, description="Keywords matching the topics")

def download_and_parse_pdf(
    title: str,
    paper_url: str,
    paper_path: str
) -> dict:
    """
    Download a PDF from er_url in paper_meta, parse, split, embed, and save chunks to a vector DB.
    Returns: {"chunks_added": N, "vector_db_path": ...} or {"error": ...}
    """                                 
    if not isinstance(paper_url, str) or not paper_url.strip():
        msg = "No paper_url provided."
        logging.error(f"[PDF] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

    if not isinstance(paper_path, str) or not paper_path.strip():
        msg = "No paper_path provided."
        logging.error(f"[PDF] {msg} (title={title!r}, url={paper_url!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})
    
    # Ensure destination directory exists
    helper_func.ensure_parent_dir(paper_path)
    
    # ---- Download ----
    logging.info(f"[PDF] Downloading (title={title!r}) from {paper_url!r} → {paper_path!r}")
    try:
        resp = paper_crawler.download_pdf(paper_url, save_path=paper_path)
    except Exception as dl_err:
        msg = f"PDF download failed: {dl_err}"
        logging.exception(f"[PDF] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url, "paper_path": paper_path})
    
    # Single, consolidated success check
    file_ok = os.path.isfile(paper_path) and os.path.getsize(paper_path) > 0
    if not file_ok:
        msg = f"PDF download incomplete (response={resp!r}, path={paper_path!r})."
        logging.error(f"[PDF] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url, "paper_path": paper_path})

    logging.info(f"[PDF] Download complete (bytes={os.path.getsize(paper_path)})")

    # ---- Parse ----
    try:
        text = ''
        docs = pymupdf.open(paper_path)
        for page in docs:
            text += page.get_text()
    except Exception as parse_err:
        msg = f"Failed to parse PDF: {parse_err}"
        logging.exception(f"[PDF] {msg} (path={paper_path!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url, "paper_path": paper_path})

    if not docs:
        msg = "Parsed 0 documents from the PDF."
        logging.warning(f"[PDF] {msg} (path={paper_path!r})")
        return helper_func.make_response(
            "warning", msg, {"title": title, "paper_url": paper_url, "paper_path": paper_path, "doc_count": 0, "docs": []}
        )

    # ---- Success ----
    logging.info(f"[PDF] Parsed {len(docs)} document(s) from {paper_path!r}")
    return helper_func.make_response(
        "success",
        f"Fetched PDF for paper '{title}' and parsed {len(docs)} document(s).",
        {"text": text}
    )

# ----------- 3. Tool: RAG Retriever -----------
class RagRetrieveArgs(BaseModel):
    title: str = Field(..., description="Metadata about the paper for filtering")
    paper_url: str = Field(..., description="URL for downloading the paper")

def create_rag_chunks(
    title: str,
    paper_url: str,
    embedding_fn: Any,
    vector_db_path: str,
    paper_path: str,
    text_splitter: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Download a paper, split into chunks, attach metadata, and index into FAISS.
    """
    # 1) Download & parse
    resp = download_and_parse_pdf(title, paper_url, paper_path)
    if resp.get("status") != "success":
        msg = f"Could not index: {resp.get('message')}"
        logging.error(f"[RAG][INDEX] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

    text = (resp.get("data") or {}).get("text") or ""
    if not isinstance(text, str) or not text.strip():
        msg = "Parsed text is empty."
        logging.error(f"[RAG][INDEX] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

    # 2) Split to Documents (your splitter already outputs Documents)
    base_doc = Document(page_content=text, metadata={"title": title, "paper_url": paper_url})
    try:
        split_docs: List[Document] = text_splitter.split_documents([base_doc])
    except Exception as e:
        msg = f"Failed to split text: {e}"
        logging.exception(f"[RAG][INDEX] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    if not split_docs:
        msg = "Text splitter returned 0 chunks."
        logging.warning(f"[RAG][INDEX] {msg} (title={title!r})")
        return helper_func.make_response("warning", msg, {"title": title, "paper_url": paper_url})

    # 3) Ensure per-chunk metadata (no shared dicts) + chunk_id
    parsed_chunks: List[Document] = []
    for idx, d in enumerate(split_docs):
        content = getattr(d, "page_content", "") or ""
        if not isinstance(content, str) or not content.strip():
            continue
        meta = {**(getattr(d, "metadata", {}) or {}), "title": title, "paper_url": paper_url, "chunk_id": idx}
        parsed_chunks.append(Document(page_content=content, metadata=meta))

    if not parsed_chunks:
        msg = "All chunks were empty after normalization."
        logging.error(f"[RAG][INDEX] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title})

    # 4) Upsert into FAISS
    try:
        if os.path.exists(vector_db_path):
            try:
                vectorstore = FAISS.load_local(vector_db_path, embedding_fn, allow_dangerous_deserialization=True)
            except TypeError:
                vectorstore = FAISS.load_local(vector_db_path, embedding_fn)
            vectorstore.add_documents(parsed_chunks)
        else:
            vectorstore = FAISS.from_documents(parsed_chunks, embedding_fn)
        vectorstore.save_local(vector_db_path)
    except Exception as e:
        msg = f"Failed to save to vector store: {e}"
        logging.exception(f"[RAG][INDEX] {msg}")
        return helper_func.make_response("error", msg, {"vector_db_path": vector_db_path})

    msg = f"Indexed {len(parsed_chunks)} chunk(s) for '{title}' into {vector_db_path}"
    logging.info(f"[RAG][INDEX] {msg}")
    return helper_func.make_response(
        "success",
        msg,
        {"paper": title, "chunks_added": len(parsed_chunks), "vector_db_path": vector_db_path},
    )

rag_retrieve_tool = StructuredTool.from_function(
    func=partial(
        create_rag_chunks,
        vector_db_path=config.VECTOR_DB_PATH,
        rag_config=config.RAG_RETRIEVER_CONFIG,
        embedding_fn=llm_provider.get_embedding_model(config),
    ),
    args_schema=RagRetrieveArgs,
    name="create_rag_retriever",
    description="Index a paper into the vector store by downloading and chunking it."
)


# ----------- 3. Tool: RAG Q&A -----------
class RagQAToolArgs(BaseModel):
    question: str = Field(..., description="Question about the paper")
    title: str = Field(..., description="Paper title to filter")
    paper_url: Optional[str] = Field(None, description="Optional paper URL for stricter filtering")

def rag_qa(
    question: str,
    title: str,
    paper_url: str,
    rag_config: Dict[str, Any],
    llm: Any,
    embedding_fn: Any,
    vector_db_path: str,
) -> Dict[str, Any]:
    """
    Answer a question by retrieving relevant chunks from the FAISS vector store.
    Filters by metadata (title, paper_url) after retrieval.
    """
    # Validate LLM
    if llm is None or not (hasattr(llm, "invoke") or callable(llm)):
        msg = "No usable LLM provided."
        logging.error(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    # Load vectorstore
    if not os.path.exists(vector_db_path):
        msg = "Vector DB not found. Index the paper first."
        logging.error(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"vector_db_path": vector_db_path})

    try:
        try:
            vectorstore = FAISS.load_local(vector_db_path, embedding_fn, allow_dangerous_deserialization=True)
        except TypeError:
            vectorstore = FAISS.load_local(vector_db_path, embedding_fn)
    except Exception as e:
        msg = f"Failed to load vector store: {e}"
        logging.exception(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"vector_db_path": vector_db_path})

    # Build retriever (FAISS doesn't support metadata server-side filtering; we'll filter post-retrieval)
    retriever = vectorstore.as_retriever(**(rag_config or {}))
    try:
        docs = retriever.get_relevant_documents(question)
    except Exception as e:
        msg = f"Retriever failed: {e}"
        logging.exception(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    # Filter by metadata (title, and paper_url if provided)
    def _match(d: Document) -> bool:
        mt = (d.metadata or {})
        if mt.get("title") != title:
            return False
        if paper_url and mt.get("paper_url") != paper_url:
            return False
        return True

    filtered = [d for d in docs if _match(d)]
    if not filtered:
        msg = "No relevant chunks found for this paper. Index it first or check the title/URL."
        logging.warning(f"[RAG][QA] {msg} (title={title!r}, url={paper_url!r})")
        return helper_func.make_response("warning", msg, {"title": title, "paper_url": paper_url})

    context = "\n\n".join(d.page_content for d in filtered if getattr(d, "page_content", ""))

    prompt = f"""Given the following paper context and metadata, answer the question thoroughly.

Paper Metadata:
title: {title}
paper_url: {paper_url or "(not provided)"}

Paper Context:
{context}

Question: {question}
Answer:"""

    # LLM call
    try:
        raw = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        logging.info(f"[RAG][QA] LLM call succeeded (title={title!r})")
        answer = (
            getattr(raw, "content", None)
            or getattr(raw, "text", None)
            or (raw.get("content") or raw.get("text")) if isinstance(raw, dict) else str(raw)
        )
    except Exception as e:
        msg = f"LLM service failed: {e}"
        logging.exception(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    return helper_func.make_response(
        "success",
        "LLM generated an answer successfully.",
        {"answer": answer, "chunks_used": len(filtered)},
    )

rag_qa_tool = StructuredTool.from_function(
    func=partial(
        rag_qa,
        llm=llm_provider.get_llm(config),
        embedding_fn=llm_provider.get_embedding_model(config),
        vector_db_path=config.VECTOR_DB_PATH,
        rag_config=config.RAG_RETRIEVER_CONFIG,
    ),
    args_schema=RagQAToolArgs,
    name="rag_qa",
    description="Answer questions about a paper using a FAISS-based retriever filtered by paper metadata."
)

# ----------- 4. Tool: Summarize Paper Insights -----------
class PaperSummaryArgs(BaseModel):
    title: str = Field(..., description="List of papers to be summarized")   
    paper_url: str = Field(..., description="URL for downloading the paper")

def summarize_paper(
    title: str,
    paper_url: str, 
    paper_path: str,
    summary_instruction: str, 
    llm: Any,
    summary_path: str, 
) -> Dict[str, Any]:

    # ---- Download & parse PDF ----
    init_resp = download_and_parse_pdf(title, paper_url, paper_path)
    if init_resp.get("status") == "error":
        msg = f"Cannot download and parse the PDF: {init_resp.get('message')}"
        logging.error(f"[SUM] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

    # Expect a single string of text now
    text = init_resp.get("data", {}).get("text")
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    if not text.strip():
        msg = "PDF parsed but returned empty text."
        logging.warning(f"[SUM] {msg} (title={title!r})")
        return helper_func.make_response("warning", msg, {"title": title, "paper_url": paper_url})

    if len(text) > config.MAX_TEXT_LENGTH:
        text = text[:config.MAX_TEXT_LENGTH]

    # ---- Build prompt ----
    prompt = f"""{summary_instruction}

**Paper Context**
{title}
{text}

**Summary**
"""

    # ---- Validate LLM ----
    if llm is None or not (hasattr(llm, "invoke") or callable(llm)):
        msg = "No usable LLM provided."
        logging.error(f"[SUM] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

    # ---- Ensure summary directory ----
    helper_func.ensure_parent_dir(summary_path)
    outfile = os.path.join(summary_path, f"{helper_func.safe_filename(title)}.md")
    
    # ---- Call LLM & save ----
    try:
        raw = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        logging.info(f"[SUM] LLM call succeeded (title={title!r})")

        answer = (
            getattr(raw, "content", None)
            or getattr(raw, "text", None)
            or (raw.get("content") or raw.get("text")) if isinstance(raw, dict) else None
        )
        if answer is None:
            answer = str(raw)

        try:
            init_resp = data_process.save_md_file(answer, outfile)
        except Exception as io_err:
            msg = f"Failed to save summary: {io_err}"
            logging.exception(f"[SUM] {msg} (outfile={outfile!r})")
            return helper_func.make_response("error", msg, None)

        if init_resp.get("status") == "error":
            msg = f"Failed to save summary: {init_resp.get('message')}"
            logging.error(f"[SUM] {msg}")
            return helper_func.make_response("error", msg, None)

        msg = f"LLM generated a summary and saved to {outfile}"
        logging.info(f"[SUM] {msg}")
        return helper_func.make_response(
            "success",
            msg,
            {"title": title, "paper_url": paper_url, "summary_path": outfile, "answer": answer},
        )

    except Exception as e:
        msg = f"LLM service failed: {e}"
        logging.exception(f"[SUM] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": paper_url})

summarize_paper_tool = StructuredTool.from_function(
    func=partial(
        summarize_paper, 
        paper_path=config.TEMP_PAPER_PATH,
        summary_instruction=prompts.PAPER_SUMMARY_PROMPT, 
        llm=llm_provider.get_llm(config),
        summary_path=config.PAPER_SUMMARY_PATH,
    ),
    args_schema=PaperSummaryArgs,
    name="summarize_paper",
    description="Given one paper title, write and save a summary to a specific instruction/template, including motivation, methodology, and results."
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
    llm: Any,
    # summary_instruction: str,
    highlight_instruction: str,
    trend_instruction: str,
    paper_db_path: str,
    # paper_path: str, 
    summary_path: str,
    trend_path: str
) -> Dict[str, Any]:
    """
    Summarize the research trend for a topic in a given conference/year by
    ensuring per-paper summaries exist, extracting/creating highlights, and
    synthesizing a trend summary.
    """
    # ---- Validate LLM once ----
    if llm is None or not (hasattr(llm, "invoke") or callable(llm)):
        msg = "No usable LLM provided."
        logging.error(f"[TREND] {msg}")
        return helper_func.make_response("error", msg, {"conference": conference, "year": year, "topic": topic})

    # ---- Ensure DB/table exists ----
    init_resp = data_process.initialize_paper_database(paper_db_path)
    if init_resp.get("status") != "success":
        msg = f"Cannot initialize database: {init_resp.get('message')}"
        logging.error(f"[TREND][INIT] {msg}")
        return helper_func.make_response("error", msg, {"paper_db_path": paper_db_path})

    # ---- Query DB ----
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, paper_url FROM papers WHERE conference=? AND year=? AND topic=?",
                (conference, year, topic),
            )
            rows = cursor.fetchall()
    except Exception as db_err:
        msg = f"DB query failed: {db_err}"
        logging.exception(f"[TREND] {msg}")
        return helper_func.make_response("error", msg, {"conference": conference, "year": year, "topic": topic})

    if not rows:
        msg = f"No papers found in database for {conference} {year} topic '{topic}'."
        logging.warning(f"[TREND] {msg}")
        return helper_func.make_response("warning", msg, {"conference": conference, "year": year, "topic": topic})

    titles: List[str] = [r[0] for r in rows]
    paper_urls: List[str] = [r[1] for r in rows]
    summary_files: List[str] = [
        os.path.join(summary_path, f"{helper_func.safe_filename(t)}.md") for t in titles
    ]
    # ---- Ensure summaries exist ----
    for t, url, summary_fp in zip(titles, paper_urls, summary_files):
        if not os.path.exists(summary_fp):
            logging.error(f"[TREND] Summary missing for {t}, trend summarization terminated.")
            return helper_func.make_response(
                "error", 
                f"Summary missing for {t}, generate summary of this paper first.", 
                {"title": t, "paper_url": url})
            # logging.info(f"[TREND] Summary missing for {t!r}; generating...")
            # sum_resp = summarize_paper(
            #     title=t,
            #     paper_url=url,
            #     paper_path=paper_path,
            #     summary_instruction=summary_instruction,
            #     llm=llm,
            #     summary_path=summary_path,  # pass the directory, not the file path
            # )
            # if sum_resp.get("status") != "success":
            #     msg = f"Failed to generate summary for '{t}': {sum_resp.get('message')}"
            #     logging.error(f"[TREND] {msg}")
            #     return helper_func.make_response("error", msg, {"title": t, "paper_url": url})

    # ---- Build highlights ----
    highlight_list: List[str] = []
    for t, summary_fp in zip(titles, summary_files):
        load_resp = data_process.load_md_file(summary_fp)
        if load_resp.get("status") != "success":
            msg = f"Failed loading summary for '{t}': {load_resp.get('message')}"
            logging.error(f"[TREND] {msg}")
            return helper_func.make_response(load_resp.get("status", "error"), msg, {"summary_path": summary_fp})

        paper_summary = load_resp.get("data") or ""

        # Try to extract "6. Highlights"
        section = data_process.get_md_section(paper_summary, section_name="6. Highlights")
        if isinstance(section, dict):
            highlight = (section.get("data") or "").strip() if section.get("status") == "success" else ""
        else:
            highlight = (section or "").strip()

        # If missing, create with LLM (inline call & extraction)
        if not highlight:
            highlight_prompt = (
                f"{highlight_instruction}\n\n"
                f"Title: {t}\n"
                f"Summary:\n{paper_summary}\n\n"
                f"Please generate a concise highlight paragraph (problem, contribution, method)."
            )
            try:
                raw = llm.invoke(highlight_prompt) if hasattr(llm, "invoke") else llm(highlight_prompt)
                highlight = (
                    getattr(raw, "content", None)
                    or getattr(raw, "text", None)
                    or (raw.get("content") or raw.get("text")) if isinstance(raw, dict) else str(raw)
                )
            except Exception as e:
                msg = f"LLM failed on highlight for '{t}': {e}"
                logging.exception(f"[TREND] {msg}")
                return helper_func.make_response("error", msg, {"title": t})

        highlight_list.append(f"- **{t}**: {str(highlight).strip()}")

    if not highlight_list:
        msg = "No highlights could be produced."
        logging.error(f"[TREND] {msg}")
        return helper_func.make_response("error", msg, {"conference": conference, "year": year, "topic": topic})

    all_highlights = "\n\n".join(highlight_list)

    # ---- Trend synthesis ----
    trend_prompt = (
        f"{trend_instruction}\n\n"
        f"Here are the highlights of all papers on topic '{topic}' at {conference} {year}:\n\n"
        f"{all_highlights}\n\n"
        f"Write a summary paragraph capturing the main trends, open challenges, and directions."
    )
    try:
        raw = llm.invoke(trend_prompt) if hasattr(llm, "invoke") else llm(trend_prompt)
        trend_summary = (
            getattr(raw, "content", None)
            or getattr(raw, "text", None)
            or (raw.get("content") or raw.get("text")) if isinstance(raw, dict) else str(raw)
        )
        trend_summary = (trend_summary or "").strip()
    except Exception as e:
        msg = f"LLM failed on trend summary: {e}"
        logging.exception(f"[TREND] {msg}")
        return helper_func.make_response("error", msg, {"conference": conference, "year": year, "topic": topic})

    # ---- Save trend markdown ----
    helper_func.ensure_parent_dir(trend_path)
    fname = f"{helper_func.safe_filename(f'{conference}_{year}_{topic}')}.md"
    md_path = os.path.join(trend_path, fname)
    content = (
        f"# Research Trend: {conference} {year} - {topic}\n\n"
        f"## Paper Highlights\n\n{all_highlights}\n\n"
        f"## Trend Summary\n\n{trend_summary}\n"
    )

    try:
        save_resp = data_process.save_md_file(content, md_path)
    except Exception as e:
        msg = f"Failed to save trend summary: {e}"
        logging.exception(f"[TREND] {msg} (path={md_path!r})")
        return helper_func.make_response("error", msg, {"trend_path": md_path})

    if isinstance(save_resp, dict) and save_resp.get("status") != "success":
        msg = f"Failed to save trend summary: {save_resp.get('message') or 'unknown error'}"
        logging.error(f"[TREND] {msg}")
        return helper_func.make_response("error", msg, {"trend_path": md_path})

    msg = f"Trend summary created at {md_path}"
    logging.info(f"[TREND] {msg}")
    return helper_func.make_response(
        "success",
        msg,
        {
            "conference": conference,
            "year": year,
            "topic": topic,
            "trend_summary_path": md_path,
            "trend_summary": trend_summary,
        },
    )

trend_summary_tool = StructuredTool.from_function(
    func=partial(
        summarize_research_trend,
        llm=llm_provider.get_llm(config),
        # summary_instruction=prompts.PAPER_SUMMARY_PROMPT,
        highlight_instruction=prompts.PAPER_HIGHLIGHT_PROMPT,
        trend_instruction=prompts.RESEARCH_TREND_PROMPT,
        summary_path=config.PAPER_SUMMARY_PATH,
        # paper_path=config.TEMP_PAPER_PATH,
        paper_db_path=config.PAPER_DB_PATH,
        trend_path=config.TREND_SUMMARY_PATH),
    args_schema=TrendSummaryArgs,
    name="summarize_research_trend",
    description="Summarize the research trend of a topic in a conference and year by synthesizing the highlights of all related papers."
)
# ----------- 5. Compose Toolkit -----------
paper_analyze_toolkit = [
    # download_and_parse_pdf_tool,
    rag_qa_tool,
    summarize_paper_tool,
    trend_summary_tool
]
