from typing import Optional, List, Dict, Any
import os
import json
import requests
from tqdm import tqdm
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
import logging
from functools import partial
import ast
import sqlite3

import sys
sys.path.append("../")
from utils import paper_crawler, prompts, data_process, helper_func
from configs import config, llm_provider


class TopicKeywordsModel(BaseModel):
    topic: str = Field(..., description="Topic of papers")
    keywords: List[str] = Field(..., description="List of keywords of a certain topic")

# class SavePaperArgs(BaseModel):
#     paper_info_list: List[Dict[str, Any]] = Field(..., description="List of paper metadata dicts")
#     conference: str = Field(..., description="Conference name")
#     year: int = Field(..., description="Year")

def save_paper_info(
    paper_info_list: List[Dict[str, Any]],
    conference: str,
    year: int,
    paper_db_path: str,
) -> Dict[str, Any]:
    """
    Insert or update paper records by title, conference, year into the SQLite database.

    Args:
        paper_info_list (list[dict]): List of paper entries to save.
        conference (str): Conference name to assign to all entries.
        year (int): Year to assign to all entries.
        paper_db_path (str): Path to the SQLite database file.
    """
    
    logging.info(f"[SAVE] Saving paper info into database {paper_db_path}")

    # Initialize DB (HTTP-style dict guaranteed)
    init_resp = data_process.initialize_paper_database(paper_db_path)
    if init_resp.get("status") == "error":
        msg = f"[INIT] Fail to initialize database: {init_resp.get('message')}"
        logging.error(f"[SAVE] {msg}")
        return helper_func.make_response("error", msg, None)
    logging.info(f"[INIT] Checked/initialized database at {paper_db_path}")

    # Validate input list
    if not isinstance(paper_info_list, list) or len(paper_info_list) == 0:
        msg = "No paper entries provided."
        logging.warning(f"[SAVE] {msg}")
        return helper_func.make_response(
            "warning",
            msg,
            {"path": paper_db_path, "inserted": 0, "updated": 0, "skipped": 0, "skipped_entries": []}
        )

    try:
        count_inserted = 0
        count_updated = 0
        skipped_entries: List[Dict[str, Any]] = []

        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()

            for idx, entry in enumerate(paper_info_list):
                # ---- validate container ----
                if not isinstance(entry, dict):
                    reason = "Paper entry is not a dict"
                    logging.error(f"[SAVE][{idx}] Skipped: {reason}")
                    skipped_entries.append({"index": idx, "title": None, "error": reason})
                    continue

                e = dict(entry)
                title = e.get("title")
                if not isinstance(title, str) or not title.strip():
                    reason = "Missing or invalid 'title'"
                    logging.error(f"[SAVE][{idx}] Skipped: {reason}")
                    skipped_entries.append({"index": idx, "title": e.get("title"), "error": reason})
                    continue

                # ---- normalize fields ----
                try:
                    e["conference"] = str(conference)
                    e["year"] = int(year)
                    e["authors"] = json.dumps(helper_func.ensure_list(e.get("authors", [])), ensure_ascii=False)
                    e["topic"] = json.dumps(helper_func.ensure_list(e.get("topic", [])), ensure_ascii=False)
                    e["keywords"] = json.dumps(helper_func.ensure_list(e.get("keywords", [])), ensure_ascii=False)
                    e["paper_url"] = str(e.get("paper_url") or "")
                except Exception as norm_err:
                    reason = f"Normalization failed: {norm_err}"
                    logging.error(f"[SAVE][{idx}] Skipped '{title}': {reason}")
                    skipped_entries.append({"index": idx, "title": title, "error": reason})
                    continue

                # ---- upsert by (title, conference, year) case-insensitive ----
                try:
                    cursor.execute(
                        "SELECT id FROM papers "
                        "WHERE title = ? COLLATE NOCASE AND conference = ? COLLATE NOCASE AND year = ?",
                        (title, e["conference"], e["year"]),
                    )
                    row = cursor.fetchone()

                    if row is None:
                        cursor.execute(
                            """
                            INSERT INTO papers (title, authors, conference, year, paper_url, topic, keywords)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                title, e["authors"], e["conference"], e["year"], 
                                e["paper_url"], e["topic"], e["keywords"]),
                        )
                        count_inserted += 1
                        logging.info(f"[SAVE][{idx}] Inserted: {title}")

                    else:
                        paper_id = row[0]
                        cursor.execute(
                            """
                            UPDATE papers
                            SET authors = ?, conference = ?, year = ?, paper_url = ?, topic = ?, keywords = ?
                            WHERE id = ?
                            """,
                            (
                                e["authors"], e["conference"], e["year"], 
                                e["paper_url"], e["topic"], e["keywords"], paper_id),
                        )
                        count_updated += 1
                        logging.info(f"[SAVE][{idx}] Updated: {title}")

                except sqlite3.Error as db_err:
                    reason = f"DB error: {db_err}"
                    logging.error(f"[SAVE][{idx}] Skipped '{title}': {reason}")
                    skipped_entries.append({"index": idx, "title": title, "error": reason})
                    continue
                except Exception as entry_err:
                    reason = f"Unexpected error: {entry_err}"
                    logging.error(f"[SAVE][{idx}] Skipped '{title}': {reason}")
                    skipped_entries.append({"index": idx, "title": title, "error": reason})
                    continue

            conn.commit()

        msg = f"Inserted {count_inserted}, updated {count_updated} papers to {paper_db_path}."
        data = {
            "path": paper_db_path,
            "inserted": count_inserted,
            "updated": count_updated,
            "skipped": len(skipped_entries),
        }

        if skipped_entries:
            status = "warning"
            msg = f"{msg} Failed inserting/updating {len(skipped_entries)} papers."
        else:
            status = "success" if (count_inserted + count_updated) > 0 else "warning"
            if status == "warning":
                msg = f"{msg} (no rows affected)"

        logging.info(f"[SAVE] {msg}")
        return helper_func.make_response(status, msg, data)

    except sqlite3.Error as e:
        msg = f"Database error during save: {e}"
        logging.error(f"[SAVE] {msg}")
        return helper_func.make_response("error", msg, None)
    except Exception as e:
        logging.exception("[SAVE] Unexpected exception during saving")
        return helper_func.make_response("error", f"Failed to save paper info: {e}", None)


class LoadPaperArgs(BaseModel):
    title: str = Field(..., description="Paper Name")

def get_paper_info_by_title(
    paper_db_path: str,
    title: str
) -> Dict[str, Any]:
    """
    Load papers from the SQLite database by exact title.

    Args:
        paper_db_path (str): Path to the SQLite database file.
        title (str): Exact title to look up.
    """
    logging.info(f"[LOAD] Looking up paper information with a given paper title.")

    # Validate input
    if not isinstance(title, str) or not title.strip():
        msg = "Empty title — cannot perform lookup."
        logging.warning(f"[LOAD] {msg}")
        return helper_func.make_response("warning", msg, {"title": title, "count": 0, "papers": []})

    # Initialize DB (guaranteed to return HTTP-style dict)
    resp = data_process.initialize_paper_database(paper_db_path)
    if resp.get("status") == "error":
        msg = f"Cannot initialize database: {resp.get('message')}"
        logging.error(f"[INIT] {msg}")
        return helper_func.make_response("error", msg, None)

    logging.info(f"[LOAD] SQL database ready at: {paper_db_path}")

    # Query
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, conference, year, paper_url, topic, keywords
                FROM papers
                WHERE title = ? COLLATE NOCASE
            """, [title])
            rows = cursor.fetchall()

        papers = []
        for row in rows:
            # Safely parse JSON-ish columns
            try:
                authors = json.loads(row[1]) if row[1] else []
            except Exception:
                authors = []
            try:
                topic = json.loads(row[5]) if row[5] else []  # CHANGED: index 6 -> 5
            except Exception:
                topic = []
            try:
                keywords = json.loads(row[6]) if row[6] else []  # FIX: parse keywords (was duplicate topic)
            except Exception:
                keywords = []

            papers.append(
                {
                    "title": row[0],
                    "authors": authors,
                    "conference": row[2],
                    "year": row[3],
                    "paper_url": row[4],
                    "topic": topic,
                    "keywords": keywords,
                }
            )

        count = len(papers)
        if count == 0:
            msg = f"No paper found with title '{title}'."
            logging.warning(f"[LOAD] {msg}")
            return helper_func.make_response(
                "warning", msg, {"title": title, "count": 0, "papers": []}
            )
        if count > 1:
            msg = f"Loaded more than one paper with title '{title}'."
            logging.warning(f"[LOAD] {msg}")
            return helper_func.make_response(
                "warning", msg, {"title": title, "count": count, "papers": papers}
            )

        msg = f"Loaded 1 paper with title '{title}'."
        logging.info(f"[LOAD] {msg}")
        return helper_func.make_response(
            "success", msg, {"title": title, "count": 1, "papers": papers}
        )

    except sqlite3.Error as e:
        msg = f"Database error during lookup: {e}"
        logging.error(f"[LOAD] {msg}")
        return helper_func.make_response("error", msg, None)
    except Exception as e:
        msg =  f"Failed to load paper info: {e}"
        logging.error(f"[LOAD] {msg}")
        return helper_func.make_response("error", msg, None)

class FilterPaperByTopicArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: TopicKeywordsModel = Field(..., description="Dict with keys 'topic' and 'keywords' (required).")


def filter_paper_by_topic(
    conference: str,
    year: int,
    topic_keywords,  # TopicKeywordsModel with: topic: str, keywords: List[str]
    paper_db_path: str
) -> Dict[str, Any]:
    """
    Filter papers for a conference/year by title keywords and/or topic membership.
    
    Args:
        conference (str): Conference name.
        year (int): Conference year.
        topic_keywords (TopicKeywordsModel): Object with .topic and .keywords.
        paper_db_path (str): Path to the SQLite database file.
    """
    # ---- Ensure table exists ----
    resp = data_process.initialize_paper_database(paper_db_path)
    if resp.get("status") == "error":
        msg = f"Cannot initialize database: {resp.get('message')}"
        logging.error(f"[FILTER][INIT] {msg}")
        return helper_func.make_response("error", msg, None)

    failed_entries: List[Dict[str, Any]] = []

    # ---- Normalize inputs ----
    topic_str = (getattr(topic_keywords, "topic", "") or "").strip()
    keywords_in: List[str] = [k for k in getattr(topic_keywords, "keywords", []) if isinstance(k, str)]
    keywords_clean = [k.strip() for k in keywords_in if k and k.strip()]
    topic_lc = topic_str.lower() if topic_str else None
    keywords_set_lc = {k.lower() for k in keywords_clean}

    if not topic_str and not keywords_set_lc:
        msg = "No topic or keywords provided."
        logging.warning(f"[FILTER] {msg}")
        return helper_func.make_response(
            "warning", msg,
            {"conference": conference, "year": year, "filtered_count": 0, "papers": [], "failed_entries": []}
        )

    # ---- Fetch base set by conference/year (NOCASE) ----
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    title,       -- 0
                    authors,     -- 1 (JSON)
                    conference,  -- 2
                    year,        -- 3
                    paper_url,   -- 4
                    topic,       -- 5 (JSON)
                    keywords     -- 6 (JSON)
                FROM papers
                WHERE conference = ? COLLATE NOCASE AND year = ?
                """,
                (conference, year),
            )
            rows = cursor.fetchall()
    except sqlite3.Error as db_err:
        msg = f"Failed to fetch papers from database {paper_db_path}: {db_err}"
        logging.exception(f"[FILTER] {msg}")
        return helper_func.make_response("error", msg, None)

    if not rows:
        msg = f"No papers found for {conference} {year}."
        logging.warning(f"[FILTER] {msg}")
        return helper_func.make_response(
            "warning", msg,
            {
                "conference": conference,
                "year": year,
                "filtered_count": 0,
                "papers": [],
                "failed_entries": [],
                "save_result": helper_func.make_response("warning", "No papers to update.", None),
            },
        )

    # ---- Match & prepare updates (keep failed_entries) ----
    filtered_papers: List[Dict[str, Any]] = []
    updated_paper_info_list: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        try:
            # Parse JSON columns safely
            try:
                authors = json.loads(row[1]) if row[1] else []
            except Exception:
                authors = []
            try:
                topic_db = json.loads(row[5]) if row[5] else []
            except Exception:
                topic_db = []
            try:
                keywords_db = json.loads(row[6]) if row[6] else []
            except Exception:
                keywords_db = []

            paper = {
                "title": row[0],
                "authors": authors,
                "conference": row[2],
                "year": row[3],
                "paper_url": row[4],
                "topic": topic_db,
                "keywords": keywords_db,
            }

            # ---- Matching（只看 topic/keywords 是否命中；大小写不敏感）----
            hit_topic = bool(topic_lc) and any(isinstance(t, str) and t.lower() == topic_lc for t in topic_db)
            kw_db_set_lc = {k.lower() for k in keywords_db if isinstance(k, str)}
            hit_kw = bool(keywords_set_lc) and bool(kw_db_set_lc & keywords_set_lc)

            if hit_topic or hit_kw:
                filtered_papers.append(paper)

                # Merge provided topic/keywords into JSON lists (dedup)
                try:
                    merged_topic = helper_func.merge_unique_elements(topic_db, [topic_str] if topic_str else [])
                    merged_keywords = helper_func.merge_unique_elements(keywords_db, keywords_clean)
                    updated_entry = dict(paper)
                    updated_entry["topic"] = merged_topic
                    updated_entry["keywords"] = merged_keywords
                    updated_paper_info_list.append(updated_entry)
                    logging.info(f"[FILTER][{idx}] Merged topic/keywords for '{paper['title']}'")
                except Exception as merge_err:
                    logging.error(f"[FILTER][{idx}] Error merging topic/keywords: {merge_err}")
                    failed_entries.append({
                        "index": idx,
                        "title": paper.get("title"),
                        "error": str(merge_err),
                    })

        except Exception as parse_err:
            logging.error(f"[FILTER][{idx}] Error parsing row: {parse_err}")
            failed_entries.append({
                "index": idx,
                "row_data": list(row),
                "error": str(parse_err),
            })

    logging.info(f"[FILTER] {len(filtered_papers)} papers matched for {conference} {year}.")

    # ---- Persist updates if any ----
    if updated_paper_info_list:
        try:
            save_result = save_paper_info(
                paper_info_list=updated_paper_info_list,
                conference=conference,
                year=year,
                paper_db_path=paper_db_path,
            )
        except Exception as save_err:
            logging.exception(f"[FILTER][UPDATE] Exception saving updated papers: {save_err}")
            save_result = helper_func.make_response("error", f"Failed to save updated papers: {save_err}", None)
    else:
        logging.info("[FILTER][UPDATE] No papers to update.")
        save_result = helper_func.make_response("warning", "No papers to update.", None)

    # ---- Final response ----
    status = "success"
    msg = f"Filtered {len(filtered_papers)} papers for {conference} {year}."
    if save_result.get("status") == "error":
        status = "error"
        msg = f"{msg} Failed to save the update papers."
    elif len(filtered_papers) == 0:
        status = "warning"
        msg = f"{msg} No new paper updates for this topic."
    elif len(failed_entries) > 0:
        status = "warning"
        msg = f"{msg} Failed updating topic/keywords for {len(failed_entries)} papers."

    return helper_func.make_response(
        status,
        msg,
        {
            "conference": conference,
            "year": year,
            "filtered_count": len(filtered_papers),
            "papers": filtered_papers,
            "failed_entries": failed_entries,  # ← 保留
            "save_result": save_result,
        },
    )

class FetchPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

def fetch_paper_list(
    conference: str,
    year: int,
    paper_db_path: str
) -> Dict[str, Any]:
    """
    Fetch a paper list for a given conference/year and persist it into the database.

    Args:
        conference: The short name of the conference to fetch (e.g., "NeurIPS").
        year: The four-digit year of the conference edition to fetch (e.g., 2024).
        paper_db_path: Filesystem path to the database where the paper list should be
            stored. If the file does not exist, it will be created.
    """
    logging.info(f"[FETCH] Fetching papers for {conference} {year}")

    # Validate inputs
    if not isinstance(conference, str) or not conference.strip():
        msg = "Empty conference name — cannot fetch."
        logging.warning(f"[FETCH] {msg}")
        return helper_func.make_response(
            "warning",
            msg,
            {"conference": conference, "year": year, "fetched": 0}
        )
    try:
        year_int = int(year)
        if year_int <= 0:
            msg = f"Year must be positive. {year_int} not valid."
            return helper_func.make_response(
                "warning",
                msg,
                {"conference": conference, "year": year, "fetched": 0}
            )
    except Exception as v_err:
        msg = f"Invalid year: {v_err}"
        logging.warning(f"[FETCH] {msg}")
        return helper_func.make_response(
            "warning",
            msg,
            {"conference": conference, "year": year, "fetched": 0}
        )

    conf_key = conference.strip().lower()

    # Supported conferences
    if conf_key == 'neurips':
        # Crawl
        try:
            papers = paper_crawler.fetch_neurips_papers(year_int)
        except Exception as crawl_err:
            msg = f"Failed to fetch {conference} {year_int}: {crawl_err}"
            logging.exception(f"[FETCH] {msg}")
            return helper_func.make_response("error", msg, None)

        if not isinstance(papers, list):
            msg = "Crawler returned a non-list payload."
            logging.error(f"[FETCH] {msg}")
            return helper_func.make_response(
                "error",
                msg,
                {"conference": conference, "year": year_int}
            )

        fetched = len(papers)
        if fetched == 0:
            msg = f"No papers fetched for {conference} {year_int}."
            logging.warning(f"[FETCH] {msg}")
            return helper_func.make_response(
                "warning",
                msg,
                {
                    "conference": conference,
                    "year": year_int,
                    "fetched": 0,
                    "save_result": helper_func.make_response("warning", "No papers to update.", None),
                }
            )

        # Save
        try:
            save_result = save_paper_info(
                paper_info_list=papers,
                conference=conference,
                year=year_int,
                paper_db_path=paper_db_path
            )
        except Exception as save_err:
            msg = f"Exception while saving papers: {save_err}"
            logging.exception(f"[FETCH] {msg}")
            return helper_func.make_response("error", msg, None)

        status = save_result.get("status", "warning")
        if status == "success":
            msg = f"Fetched and saved {fetched} papers for {conference} {year_int}."
        elif status == "warning":
            msg = f"Fetched {fetched} papers for {conference} {year_int}, but no rows were changed."
        else:
            msg = f"Fetched {fetched} papers for {conference} {year_int}, but failed to save."

        logging.info(f"[FETCH] {msg}")
        return helper_func.make_response(
            status,
            msg,
            {
                "conference": conference,
                "year": year_int,
                "fetched": fetched,
                "save_result": save_result,
            }
        )

    # Unsupported conference
    msg = f"Crawling not supported for {conference}."
    logging.warning(f"[FETCH] {msg}")
    return helper_func.make_response(
        "warning",
        msg,
        {"conference": conference, "year": year, "fetched": 0}
    )

### -----------------
    
class GenerateKeywordListArgs(BaseModel):
    topic: str = Field(..., description="The research topic or subject to generate keywords for, for instance ['privacy'].")

def generate_keyword_list(
    topic: str,
    llm: Any,
    instruction: str
) -> Dict[str, Any]:
    """
    Generate keywords for a topic using an LLM with a few-shot style prompt.
    """
    # CHANGED: tighter LLM validation (single check for None / unusable client)
    if llm is None or not (hasattr(llm, "invoke") or callable(llm)):
        msg = "No usable LLM provided to generate keywords."
        logging.error("[KEYWORD_GEN] %s (topic=%r)", msg, topic)
        return helper_func.make_response("error", msg, {"topic": topic})

    prompt = f"""{instruction}

Now, do the same for this topic:
Topic: "{topic}"
Output:
"""

    try:
        logging.info(f"[KEYWORD_GEN] Sending prompt for topic={topic!r}")

        try:
            raw = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        except Exception as call_err:
            msg = f"LLM call failed: {call_err}"
            logging.exception(f"[KEYWORD_GEN] {msg}")
            return helper_func.make_response("error", msg, {"topic": topic})

        response_text = (
            getattr(raw, "content", None)
            or getattr(raw, "text", None)
            or (raw.get("content") or raw.get("text")) if isinstance(raw, dict) else None
        )
        if response_text is None:
            response_text = str(raw)

        logging.info(f"[KEYWORD_GEN] Raw response (first 200): {response_text[:200]}")

        cleaned = helper_func.strip_code_block(response_text)

        try:
            parsed = json.loads(cleaned)
            logging.info("[KEYWORD_GEN] Successfully parsed LLM output as JSON.")
        except Exception as json_err:
            logging.warning(f"[KEYWORD_GEN] JSON parsing failed: {json_err}; trying ast.literal_eval...")
            try:
                parsed = ast.literal_eval(cleaned)
                logging.info("[KEYWORD_GEN] Successfully parsed LLM output with ast.literal_eval.")
            except Exception as parse_err:
                msg = f"Failed to parse LLM output as JSON or Python: {parse_err}"
                logging.exception(f"[KEYWORD_GEN] {msg}")
                return helper_func.make_response(
                    "error", msg, {"topic": topic, "raw_response": response_text[:200]}
                )


        # Expect the usual structure but we will ignore the model's 'topic' value
        if not isinstance(parsed, dict) or not isinstance(parsed.get("topic"), str) or not isinstance(parsed.get("keywords"), list):
            msg = "Output did not match expected data structure. Expected a dict with following fields: 'topic' (str) and 'keywords' (list)."
            logging.error(f"[KEYWORD_GEN] {msg}: {parsed!r}")
            return helper_func.make_response(
                "error", msg, {"topic": topic, "raw_response": response_text[:500]}
            )

        parsed_topic = parsed["topic"].strip()
        if parsed_topic and parsed_topic.strip().lower() != topic.strip().lower():
            logging.info(f"[KEYWORD_GEN] Ignoring model topic {parsed_topic!r}; using input topic {topic!r}.")

        # Always use the original input topic in outputs
        output_topic = topic
        
        keywords_out: List[str] = [
            k.strip().lower()
            for k in helper_func.ensure_list(parsed["keywords"])
            if isinstance(k, str) and k.strip()
        ]

        if not keywords_out:
            msg = "Parsed output but no keywords were extracted."
            logging.warning(f"[KEYWORD_GEN] {msg} (topic={output_topic!r})")
            return helper_func.make_response(
                "warning", msg, {"topic": output_topic, "keywords": []}
            )

        logging.info(f"[KEYWORD_GEN] Extracted {len(keywords_out)} keywords for topic={output_topic!r}")
        return helper_func.make_response(
            "success",
            f"Extracted keywords for topic '{output_topic}'.",
            {"topic": output_topic, "keywords": keywords_out},
        )

    except Exception as e:
        msg = f"Could not parse LLM output: {e}"
        logging.exception(f"[KEYWORD_GEN] {msg} (topic={topic!r})")
        safe_raw = (locals().get("response_text") or "")[:500]
        return helper_func.make_response("error", msg, {"topic": topic, "raw_response": safe_raw})

### -----------------

class DeleteCriteria(BaseModel):
    """
    Deletion criteria. If `all` is True, all rows are deleted and other fields are ignored.

    topic semantics:
      - topic == "null" or "[]" (case-insensitive) → delete only rows where topic JSON is exactly []
      - topic == "<label>" → delete rows whose topic list contains <label> (case-insensitive membership)
      - topic omitted/None/"" → ignore topic filter
    """
    all: bool = Field(False, description="Delete all rows when True; ignore other filters.")
    title: Optional[str] = Field(None, description="Exact title to match.")
    conference: Optional[str] = Field(None, description="Conference to match (exact).")
    year: Optional[int] = Field(None, description="Year to match (exact).")
    topic: Optional[str] = Field(None, description='Either "null"/"[]" or a topic label (string).')


class DeletePapersByCriteriaArgs(BaseModel):
    criteria: DeleteCriteria = Field(..., description="Deletion criteria dict.")
    paper_db_path: str = Field(..., description="Path to the SQLite database file.")

def delete_papers_by_criteria(
    criteria: DeleteCriteria,
    paper_db_path: str,
) -> Dict[str, Any]:
    """
    Delete papers from the database according to the given criteria.

    Args:
        criteria: Deletion rules as a dict-like object with fields in DeleteCriteria:
        paper_db_path: Filesystem path to the SQLite database file. If the file
            does not exist, it will be created.
    """
    
    # Ensure DB/table exists
    resp = data_process.initialize_paper_database(paper_db_path)
    if resp.get("status") == "error":
        msg = f"Cannot initialize database: {resp.get('message')}"
        logging.error(f"[DELETE][INIT] {msg}")
        return helper_func.make_response("error", msg, {"criteria": criteria.dict()})

    # Normalize inputs
    title = criteria.title.strip() if isinstance(criteria.title, str) else None
    conference = criteria.conference.strip() if isinstance(criteria.conference, str) else None
    year_val = int(criteria.year) if isinstance(criteria.year, int) else None
    topic_raw = criteria.topic.strip() if isinstance(criteria.topic, str) else None

    # Safety: if not all=True and no filters, refuse to avoid accidental blanket delete
    if not criteria.all and not any([title, conference, year_val is not None, topic_raw]):
        msg = "When 'all' is False, provide at least one of: title, conference, year, topic."
        logging.error(f"[DELETE] {msg}")
        return helper_func.make_response("error", msg, {"criteria": criteria.dict()})

    # 1) Delete-all path
    if criteria.all:
        try:
            with sqlite3.connect(paper_db_path) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM papers")
                deleted = cur.rowcount or 0
            status = "success" if deleted > 0 else "warning"
            msg = f"Deleted {deleted} row(s)." if deleted > 0 else "No rows to delete."
            return helper_func.make_response(status, msg, {"mode": "all", "deleted": deleted, "path": paper_db_path})
        except sqlite3.Error as e:
            msg = f"Database error during delete-all: {e}"
            logging.exception(f"[DELETE] {msg}")
            return helper_func.make_response("error", msg, {"mode": "all"})

    # Build base WHERE for title/conference/year
    where_parts: List[str] = []
    params: List[Any] = []
    if title:
        where_parts.append("title = ? COLLATE NOCASE")
        params.append(title)
    if conference:
        where_parts.append("conference = ? COLLATE NOCASE")
        params.append(conference)
    if year_val is not None:
        where_parts.append("year = ?")
        params.append(year_val)
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"

    # Topic mode
    topic_mode: Optional[str] = None   # None | 'null' | 'name'
    topic_name_lc: Optional[str] = None
    if topic_raw:
        if topic_raw.lower() in {"null", "[]"}:
            topic_mode = "null"
        else:
            topic_mode = "name"
            topic_name_lc = topic_raw.lower()

    # 2) null-topic-only: delete rows whose topic JSON is exactly [] (whitespace ignored), with base filters
    if topic_mode == "null":
        try:
            with sqlite3.connect(paper_db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    DELETE FROM papers
                    WHERE {where_sql}
                      AND REPLACE(TRIM(topic), ' ', '') = '[]'
                    """,
                    params,
                )
                deleted = cur.rowcount or 0
            status = "success" if deleted > 0 else "warning"
            msg = (f"Deleted {deleted} row(s) with null topic."
                   if deleted > 0 else "No rows with null topic matched the criteria.")
            return helper_func.make_response(
                status, msg, {"mode": "null_topic", "deleted": deleted, "path": paper_db_path, "criteria": criteria.dict()}
            )
        except sqlite3.Error as e:
            msg = f"Database error during null-topic deletion: {e}"
            logging.exception(f"[DELETE] {msg}")
            return helper_func.make_response("error", msg, {"criteria": criteria.dict()})

    # 3) Topic label membership: select candidates then delete IDs whose topic list contains the label (case-insensitive)
    if topic_mode == "name" and topic_name_lc:
        try:
            with sqlite3.connect(paper_db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT id, topic
                    FROM papers
                    WHERE {where_sql}
                    """,
                    params,
                )
                rows = cur.fetchall()
        except sqlite3.Error as e:
            msg = f"Database error during selection: {e}"
            logging.exception(f"[DELETE] {msg}")
            return helper_func.make_response("error", msg, {"criteria": criteria.dict()})

        if not rows:
            return helper_func.make_response(
                "warning",
                "No rows matched the selection criteria.",
                {"criteria": criteria.dict(), "selected": 0, "deleted": 0},
            )

        ids_to_delete: List[int] = []
        for row_id, topic_text in rows:
            try:
                topic_list = json.loads(topic_text) if topic_text else []
            except Exception:
                topic_list = []
            topic_list_lc = {t.lower() for t in topic_list if isinstance(t, str)}
            if topic_name_lc in topic_list_lc:  # membership
                ids_to_delete.append(row_id)

        if not ids_to_delete:
            return helper_func.make_response(
                "warning",
                f"No rows had topic '{criteria.topic}'.",
                {"criteria": criteria.dict(), "selected": len(rows), "deleted": 0},
            )

        deleted_total = 0
        try:
            with sqlite3.connect(paper_db_path) as conn:
                cur = conn.cursor()
                CHUNK = 800
                for i in range(0, len(ids_to_delete), CHUNK):
                    chunk = ids_to_delete[i : i + CHUNK]
                    qmarks = ",".join("?" for _ in chunk)
                    cur.execute(f"DELETE FROM papers WHERE id IN ({qmarks})", chunk)
                    deleted_total += cur.rowcount or 0
        except sqlite3.Error as e:
            msg = f"Database error during deletion: {e}"
            logging.exception(f"[DELETE] {msg}")
            return helper_func.make_response(
                "error", msg, {"criteria": criteria.dict(), "selected": len(rows), "deleted": deleted_total}
            )

        status = "success" if deleted_total > 0 else "warning"
        msg = f"Deleted {deleted_total} row(s)." if deleted_total > 0 else "No rows deleted."
        return helper_func.make_response(
            status, msg, {"criteria": criteria.dict(), "selected": len(rows), "deleted": deleted_total, "path": paper_db_path}
        )

    # 4) No topic filter: delete by base WHERE only
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM papers WHERE {where_sql}", params)
            deleted = cur.rowcount or 0
        status = "success" if deleted > 0 else "warning"
        msg = f"Deleted {deleted} row(s)." if deleted > 0 else "No rows matched the selection criteria."
        return helper_func.make_response(
            status, msg, {"mode": "base_where", "deleted": deleted, "path": paper_db_path, "criteria": criteria.dict()}
        )
    except sqlite3.Error as e:
        msg = f"Database error during deletion: {e}"
        logging.exception(f"[DELETE] {msg}")
        return helper_func.make_response("error", msg, {"criteria": criteria.dict()})

# save_paper_tool = StructuredTool.from_function(
#     func=partial(save_paper_info, paper_db_path=config.PAPER_DB_PATH),
#     args_schema=SavePaperArgs,
#     name="save_paper_info",
#     description="Save a list of paper metadata (title, authors, abstract, urls) to the SQL database. Optionally grouped by topic."
# )
get_paper_info_tool = StructuredTool.from_function(
    func=partial(get_paper_info_by_title, paper_db_path=config.PAPER_DB_PATH),
    args_schema=LoadPaperArgs,
    name="load_paper_list",
    description="Load paper metadata from the SQL database for a given conference and year. Optionally filter by topic."
)
filter_paper_by_topic_tool = StructuredTool.from_function(
    func=partial(filter_paper_by_topic, paper_db_path=config.PAPER_DB_PATH),
    args_schema=FilterPaperByTopicArgs,
    name="filter_paper_by_topic",
    description="Filter papers in the SQL database by a topic's keywords, for a conference and year."
)
fetch_paper_list_tool = StructuredTool.from_function(
    func=partial(fetch_paper_list, paper_db_path=config.PAPER_DB_PATH),
    args_schema=FetchPaperArgs,
    name="fetch_paper_list",
    description="Fetch all papers for a given conference and year, dedupe, and save new to SQL database."
)

keyword_generation_tool = StructuredTool.from_function(
    func=partial(generate_keyword_list, 
                 llm=llm_provider.get_llm(config), 
                 instruction=prompts.KEYWORDS_GENERATION_PROMPT),
    args_schema=GenerateKeywordListArgs,
    name="generate_keyword_list_given_topic",
    description="Given a research topic or concept, generate a list of keywords using an LLM."
)

delete_papers_by_criteria_tool = StructuredTool.from_function(
    func=partial(delete_papers_by_criteria, paper_db_path=config.PAPER_DB_PATH),
    args_schema=DeletePapersByCriteriaArgs,
    name="delete_papers_by_criteria",
    description=(
        "Delete rows from the 'papers' SQLite table using a dict criteria. "
        "If criteria.all is True, deletes all rows. Otherwise, filters by any of: "
        "title (exact), conference (exact), year (exact). "
        'If criteria.topic == "null" or "[]", deletes only rows whose topic JSON is exactly []; '
        "if it's any other non-null string, deletes rows whose topic list contains that label "
        "(membership check, case-insensitive). If criteria.topic is omitted, topic is ignored."
    )
)


paper_fetch_toolkit = [
    # save_paper_tool,
    get_paper_info_tool,
    fetch_paper_list_tool,
    filter_paper_by_topic_tool,
    keyword_generation_tool,
    delete_papers_by_criteria_tool
]
