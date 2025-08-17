# -*- coding: utf-8 -*-
"""
Per-paper RAG: build one FAISS store per paper at
<root>/<conference>/<year>/<safe_title>. rag_qa loads it if present returns an actionable error if missing.
"""

import os
import shutil
import logging
from functools import partial
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, AnyUrl
from langchain.tools import StructuredTool
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from configs import config, llm_provider
from utils import paper_crawler, helper_func


# ---------- Helper: per-paper vector store path (conference as-is, year -> str, title -> safe filename) ----------
def _get_paper_vs_path(root_dir: str, conference: str, year: int, title: str) -> str:
    """
    Build per-paper storage path: <root>/<conference>/<year>/<safe_title>.
    Note: 'conference' is not sanitized; 'title' is converted to a safe filename.
    """
    safe_title = helper_func.safe_filename(title)
    return os.path.join(root_dir, conference, str(year), safe_title)


# ---------- 1) Indexer: build vector store for a single paper ----------
class RagRetrieveArgs(BaseModel):
    conference: str = Field(..., description="Conference name (e.g., NeurIPS)")
    year: int = Field(..., description="Year (e.g., 2024)")
    title: str = Field(..., description="Paper title")
    paper_url: AnyUrl = Field(..., description="Direct PDF URL of the paper")

def create_paper_vs(
    conference: str,
    year: int,
    title: str,
    paper_url: AnyUrl,
    embedding_fn: Any,
    vector_db_root: str,
    paper_path: str,
    text_splitter: Any,   # your splitter returns List[Document]
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Download -> parse -> split -> build a FAISS vector store that contains only this paper
    and save it to a dedicated directory.

    If overwrite=False (default) and the store already exists, skip rebuilding and return success.
    If overwrite=True, rebuild via an atomic replace.
    """
    paper_vs_path = _get_paper_vs_path(vector_db_root, conference, year, title)
    helper_func.ensure_parent_dir(paper_vs_path)

    # Fast-path: do not overwrite an existing store unless explicitly asked
    if os.path.exists(paper_vs_path) and not overwrite:
        msg = f"Vector store for paper {title} already exists; skipping rebuild (overwrite=False): {paper_vs_path}"
        logging.info(f"[RAG][INDEX] {msg}")
        return helper_func.make_response(
            "success", msg,
            {"conference": conference, "year": year, "paper": title, "chunks_added": 0, "paper_vs_path": paper_vs_path},
        )

    # 1) Download PDF
    try:
        dl_resp = paper_crawler.download_pdf(str(paper_url), save_path=paper_path)
    except Exception as e:
        msg = f"Download failed: {e}"
        logging.exception(f"[RAG][DOWNLOAD] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": str(paper_url)})

    ok = dl_resp.get("status") == "success" if isinstance(dl_resp, dict) else (dl_resp == "success")
    if not ok:
        msg = f"Could not download paper: {getattr(dl_resp, 'get', lambda *_: None)('message') or dl_resp}"
        logging.error(f"[RAG][DOWNLOAD] {msg}")
        return helper_func.make_response("error", msg, {"title": title, "paper_url": str(paper_url), "paper_path": paper_path})
    logging.info(f"[RAG][DOWNLOAD] Downloaded '{title}' from {paper_url}.")

    # 2) Parse PDF
    try:
        parse_resp = paper_crawler.parse_pdf(paper_path)
    except Exception as e:
        msg = f"Parse failed: {e}"
        logging.exception(f"[RAG][PARSE] {msg}")
        return helper_func.make_response("error", msg, {"paper_path": paper_path})

    if parse_resp.get("status") != "success":
        msg = f"Could not parse paper: {parse_resp.get('message')}"
        logging.error(f"[RAG][PARSE] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    text = (parse_resp.get("data") or {}).get("text") or ""
    if not isinstance(text, str) or not text.strip():
        msg = "Parsed text is empty."
        logging.error(f"[RAG][INDEX] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {"title": title})

    # 3) Split into Documents (splitter already returns Documents)
    base_doc = Document(page_content=text, metadata={
        "conference": conference,
        "year": year,
        "title": title,
        "paper_url": str(paper_url),
    })
    try:
        split_docs: List[Document] = text_splitter.split_documents([base_doc])
    except Exception as e:
        msg = f"Failed to split text: {e}"
        logging.exception(f"[RAG][INDEX] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    if not split_docs:
        msg = "Text splitter returned 0 chunks."
        logging.warning(f"[RAG][INDEX] {msg} (title={title!r})")
        return helper_func.make_response("warning", msg, {"title": title})

    # 4) Normalize metadata + add chunk_id
    parsed_chunks: List[Document] = []
    for idx, d in enumerate(split_docs):
        content = getattr(d, "page_content", "") or ""
        if not content.strip():
            continue
        meta = {**(getattr(d, "metadata", {}) or {}), "chunk_id": idx}
        parsed_chunks.append(Document(page_content=content, metadata=meta))

    if not parsed_chunks:
        msg = "All chunks were empty after normalization."
        logging.error(f"[RAG][INDEX] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    # 5) Save using atomic replace when overwriting
    tmp_path = paper_vs_path + ".tmp"
    try:
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)

        vectorstore = FAISS.from_documents(parsed_chunks, embedding_fn)
        vectorstore.save_local(tmp_path, safe_serialization=True)

        if os.path.exists(paper_vs_path):
            shutil.rmtree(paper_vs_path)
        os.replace(tmp_path, paper_vs_path)  # atomic directory swap on most OSes
    except Exception as e:
        msg = f"Failed to build/save vector store: {e}"
        logging.exception(f"[RAG][INDEX] {msg}")
        # best-effort cleanup
        try:
            if os.path.exists(tmp_path):
                shutil.rmtree(tmp_path)
        except Exception:
            pass
        return helper_func.make_response("error", msg, {"paper_vs_path": paper_vs_path})

    msg = f"Indexed {len(parsed_chunks)} chunk(s) for '{title}' at {paper_vs_path}"
    logging.info(f"[RAG][INDEX] {msg}")
    return helper_func.make_response(
        "success",
        msg,
        {"conference": conference, "year": year, "paper": title, "chunks_added": len(parsed_chunks), "paper_vs_path": paper_vs_path},
    )


create_paper_vs_tool = StructuredTool.from_function(
    func=partial(
        create_paper_vs,
        vector_db_root=config.VECTOR_DB_PATH, # root for per-paper stores
        embedding_fn=llm_provider.get_embedding_model(config),
        paper_path=config.TEMP_PAPER_PATH,
        text_splitter=llm_provider.get_text_splitter(config),
        overwrite=True,   # explicit tool action can refresh/rebuild if desired
    ),
    args_schema=RagRetrieveArgs,
    name="create_paper_vs",
    description="Index a single paper into its own FAISS vector store (paper_vs), which named by conference/year/title)."
)


# ---------- 2) RAG QA: use if exists; create if missing (never overwrite existing) ----------
class RagQAToolArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    title: str = Field(..., description="Paper title")
    question: str = Field(..., description="Question about the paper")

def rag_qa(
    conference: str,
    year: int,
    title: str,
    question: str,
    rag_config: Dict[str, Any],
    llm: Any,
    embedding_fn: Any,
    vector_db_root: str,
) -> Dict[str, Any]:
    """
    Use an existing per-paper FAISS store. If missing, return an error so the agent
    can call `create_paper_vs(..., overwrite=True)` to (re)build it.
    """
    # Validate LLM
    if llm is None or not (hasattr(llm, "invoke") or callable(llm)):
        msg = "No usable LLM provided."
        logging.error(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"conference": conference, "year": year, "title": title})

    # Compute per-paper path
    paper_vs_path = _get_paper_vs_path(vector_db_root, conference, year, title)
    helper_func.ensure_parent_dir(paper_vs_path)

    if not os.path.exists(paper_vs_path):
        msg = f"Vector store for paper {paper_vs_path} is missing. Build it first."
        logging.error(f"[RAG][QA] {msg}")
        return helper_func.make_response(
            "error",
            msg,
            {"paper_vs_path": paper_vs_path, "suggested_action": "create_paper_vs_tool", "overwrite": True},
        )

    # Load existing store
    try:
        try:
            vectorstore = FAISS.load_local(paper_vs_path, embedding_fn, allow_dangerous_deserialization=True)
        except TypeError:
            vectorstore = FAISS.load_local(paper_vs_path, embedding_fn)
    except Exception as e:
        msg = (
            f"Vector store for paper {paper_vs_path} exists, but failed to load: {e}. "
            f"Try rebuilding it with overwrite=True."
        )
        logging.exception(f"[RAG][QA] {msg}")
        return helper_func.make_response(
            "error",
            msg,
            {"paper_vs_path": paper_vs_path, "suggested_action": "create_paper_vs_tool", "overwrite": True},
        )

    # Retrieve (store contains only this paper)
    retriever = vectorstore.as_retriever(**(rag_config or {}))
    try:
        docs: List[Document] = retriever.get_relevant_documents(question)
    except Exception as e:
        msg = f"Retriever failed: {e}"
        logging.exception(f"[RAG][QA] {msg}")
        return helper_func.make_response("error", msg, {"title": title})

    if not docs:
        msg = "No relevant chunks found."
        logging.warning(f"[RAG][QA] {msg}")
        return helper_func.make_response("warning", msg, {"title": title})

    # Optional: trim context
    max_ctx = getattr(config, "MAX_CONTEXT_CHARS", None)
    context_full = "\n\n".join(d.page_content for d in docs if getattr(d, "page_content", ""))
    context = context_full[:max_ctx] if isinstance(max_ctx, int) and max_ctx > 0 else context_full

    prompt = f"""Given the following paper context, answer the question thoroughly.

Paper:
conference: {conference}
year: {year}
title: {title}

Context:
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
        {"answer": answer, "chunks_used": len(docs), "paper_vs_path": paper_vs_path},
    )

rag_qa_tool = StructuredTool.from_function(
    func=partial(
        rag_qa,
        llm=llm_provider.get_llm(config),
        embedding_fn=llm_provider.get_embedding_model(config),
        vector_db_root=config.VECTOR_DB_PATH,
        rag_config=config.RAG_RETRIEVER_CONFIG,
    ),
    args_schema=RagQAToolArgs,
    name="rag_qa",
    description="Use an existing per-paper FAISS vector store (paper_vs); if missing, return an error so the agent can rebuild it."
)

paper_rag_toolkit = [
    create_paper_vs_tool,
    rag_qa_tool
]
