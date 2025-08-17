import os
import json
import sys
sys.path.append("../")
from pydantic import BaseModel, Field, AnyUrl
from typing import Dict, Any, List
from functools import partial
import logging
import sqlite3
from langchain.tools import StructuredTool

from configs import config, llm_provider
from utils import prompts, paper_crawler, data_process, helper_func

# TODO: check whether conference, year, paper_url is valid

# ----------- 1. Tool: Summarize Paper Insights -----------
class PaperSummaryArgs(BaseModel):
    title: str = Field(..., description="Title of the paper to summarize.")
    conference: str = Field(..., description="Conference name (e.g., NeurIPS)")
    year: int = Field(..., description="Year")
    paper_url: AnyUrl = Field(..., description="Direct URL to download the paper PDF.")
    rewrite: bool = Field(False, description="If true, overwrite an existing summary; otherwise reuse it.")

def summarize_paper(
    title: str,
    conference: str,
    year: int, 
    paper_url: str, 
    paper_path: str,
    summary_instruction: str, 
    llm: Any,
    summary_path: str, 
    rewrite: bool = False,
) -> Dict[str, Any]:
    # ---- Output path (summary_path is a directory) ----
    outfile = os.path.join(summary_path, conference, year, f"{helper_func.safe_filename(title)}.md")
    helper_func.ensure_parent_path(outfile)

    # ---- If summary exists and rewrite is False, return it directly ----
    if os.path.exists(outfile) and not rewrite:
        try:
            with open(outfile, "r", encoding="utf-8") as f:
                existing = f.read()
        except Exception as io_err:
            msg = f"Found existing summary but failed to read it: {io_err}"
            logging.exception(f"[SUM] {msg} (outfile={outfile!r})")
            return helper_func.make_response("error", msg, {
                "title": title, "paper_url": paper_url, "summary_path": outfile
            })

        msg = f"Using existing summary at {outfile} (rewrite=False)."
        logging.info(f"[SUM] {msg}")
        return helper_func.make_response(
            "success",
            msg,
            {"title": title, "paper_url": paper_url, "summary_path": outfile, "answer": existing},
        )

    # ---- Ensure directory for outfile ----
    helper_func.ensure_parent_dir(outfile)

    # ---- Download PDF ----
    resp_dl = paper_crawler.download_pdf(paper_url, paper_path)
    if resp_dl.get("status") != "success":
        msg = f"Could not download paper: {resp_dl.get('message')}"
        logging.error(f"[RAG][DOWNLOAD] {msg}")
        return helper_func.make_response("error", msg, {
            "title": title, "paper_url": paper_url, "paper_path": paper_path
        })
    logging.info(f"[RAG][DOWNLOAD] Downloaded paper '{title}' from {paper_url}.")

    # ---- Parse PDF ----
    resp_parse = paper_crawler.parse_pdf(paper_path)
    if resp_parse.get("status") != "success":
        msg = f"Could not parse paper: {resp_parse.get('message')}"
        logging.error(f"[RAG][PARSE] {msg}")
        return helper_func.make_response("error", msg, {
            "title": title, "paper_url": paper_url, "paper_path": paper_path
        })
    logging.info(f"[RAG][PARSE] Parsed paper '{title}'.")

    # ---- Extract and bound text ----
    text = resp_parse.get("data", {}).get("text")
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    if not text.strip():
        msg = "PDF parsed but returned empty text."
        logging.warning(f"[SUM] {msg} (title={title!r})")
        return helper_func.make_response("warning", msg, {
            "title": title, "paper_url": paper_url
        })

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
        return helper_func.make_response("error", msg, {
            "title": title, "paper_url": paper_url
        })

    # ---- Call LLM & save ----
    try:
        raw = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        logging.info(f"[SUM] LLM call succeeded (title={title!r})")

        answer = (
            getattr(raw, "content", None)
            or getattr(raw, "text", None)
            or ((raw.get("content") or raw.get("text")) if isinstance(raw, dict) else None)
        )
        if answer is None:
            answer = str(raw)

        if not isinstance(answer, str):
            answer = str(answer)
        if not answer.strip():
            msg = "LLM returned an empty summary."
            logging.error(f"[SUM] {msg}")
            return helper_func.make_response("error", msg, {
                "title": title, "paper_url": paper_url
            })

        try:
            save_resp = data_process.save_md_file(answer, outfile)  # assume overwrite behavior
        except Exception as io_err:
            msg = f"Failed to save summary: {io_err}"
            logging.exception(f"[SUM] {msg} (outfile={outfile!r})")
            return helper_func.make_response("error", msg, None)

        if save_resp.get("status") == "error":
            msg = f"Failed to save summary: {save_resp.get('message')}"
            logging.error(f"[SUM] {msg}")
            return helper_func.make_response("error", msg, None)

        msg = f"LLM generated a summary and saved to {outfile}" + (" (overwritten)" if rewrite else "")
        logging.info(f"[SUM] {msg}")
        return helper_func.make_response(
            "success",
            msg,
            {"title": title, "paper_url": paper_url, "summary_path": outfile, "answer": answer},
        )

    except Exception as e:
        msg = f"LLM service failed: {e}"
        logging.exception(f"[SUM] {msg} (title={title!r})")
        return helper_func.make_response("error", msg, {
            "title": title, "paper_url": paper_url
        })
    
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

# ----------- 2. Tool: Summarize Research Trend -----------
class TrendSummaryArgs(BaseModel):
    conference: str = Field(..., description="Conference name (e.g., NeurIPS)")
    year: int = Field(..., description="Year")
    topic: str = Field(..., description="Research topic (e.g., privacy, LLM)")

def summarize_research_trend(
    conference: str,
    year: int,
    topic: str,
    llm: Any,
    highlight_instruction: str,
    trend_instruction: str,
    paper_db_path: str,
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
            try:
                # [FIX] topic JSON membership + NOCASE on text columns
                cursor.execute(
                    """
                    SELECT p.title, p.paper_url
                    FROM papers AS p
                    JOIN json_each(p.topic) AS t
                    WHERE p.conference = ? COLLATE NOCASE
                    AND p.year = ?
                    AND t.value = ? COLLATE NOCASE
                    """,
                    (conference, year, topic),
                )
                rows = cursor.fetchall()

            except sqlite3.OperationalError as oe:
                # Likely "no such function: json_each" → fallback to Python filtering
                logging.warning(f"[TREND] JSON1 unavailable ({oe}); falling back to client-side filter.")
                cursor.execute(
                    """
                    SELECT title, paper_url, topic
                    FROM papers
                    WHERE conference = ? COLLATE NOCASE
                    AND year = ?
                    """,
                    (conference, year),
                )
                raw = cursor.fetchall()
                topic_lc = (topic or "").lower()
                rows = []
                for title, url, topic_text in raw:
                    try:
                        arr = json.loads(topic_text) if topic_text else []
                    except Exception:
                        arr = []
                    if any(isinstance(t, str) and t.lower() == topic_lc for t in arr):
                        rows.append((title, url))

    except sqlite3.Error as db_err:
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
        os.path.join(summary_path, conference, year, f"{helper_func.safe_filename(t)}.md") for t in titles
    ]
    # ---- Ensure summaries exist ----
    for t, url, summary_fp in zip(titles, paper_urls, summary_files):
        if not os.path.exists(summary_fp):
            logging.error(f"[TREND] Summary missing for {t}, trend summarization terminated.")
            return helper_func.make_response(
                "error", 
                f"Summary missing for {t}, generate summary of this paper first.", 
                {"title": t, "paper_url": url, "suggested_action": "summarize_paper_tool"})
        
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
    fname = f"{helper_func.safe_filename(f'{conference}_{year}_{topic}')}.md"
    md_path = os.path.join(trend_path, fname)
    helper_func.ensure_parent_dir(md_path)
    
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
        highlight_instruction=prompts.PAPER_HIGHLIGHT_PROMPT,
        trend_instruction=prompts.RESEARCH_TREND_PROMPT,
        summary_path=config.PAPER_SUMMARY_PATH,
        paper_db_path=config.PAPER_DB_PATH,
        trend_path=config.TREND_SUMMARY_PATH),
    args_schema=TrendSummaryArgs,
    name="summarize_research_trend",
    description="Summarize the research trend of a topic in a conference and year by synthesizing the highlights of all related papers."
)
# ----------- 5. Compose Toolkit -----------
paper_summary_toolkit = [
    summarize_paper_tool,
    trend_summary_tool
]
