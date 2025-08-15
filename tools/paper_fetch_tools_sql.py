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
                try:
                    if not isinstance(entry, dict):
                        raise TypeError("Paper entry is not a dict")

                    e = dict(entry)  # shallow copy for normalization
                    title = e.get("title")
                    if not isinstance(title, str) or not title.strip():
                        raise ValueError("Paper entry missing 'title'")

                    # Normalize/assign fields (no abstract handling)
                    e["conference"] = str(conference)
                    e["year"] = int(year)
                    e["authors"]  = json.dumps(helper_func.ensure_list(e.get("authors", [])))
                    e["topic"]    = json.dumps(helper_func.ensure_list(e.get("topic", [])))
                    e["keywords"] = json.dumps(helper_func.ensure_list(e.get("keywords", [])))
                    e["paper_url"] = str(e.get("paper_url", ""))

                    # Upsert by title
                    cursor.execute("SELECT id FROM papers WHERE title = ?", (title,))
                    row = cursor.fetchone()

                    if row is None:
                        # INSERT (no abstract column)
                        cursor.execute(
                            """
                            INSERT INTO papers (title, authors, conference, year, paper_url, topic, keywords)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                title, e["authors"], e["conference"], e["year"],
                                e["paper_url"], e["topic"], e["keywords"]
                            )
                        )
                        count_inserted += 1
                        logging.info(f"[SAVE][{idx}] Inserted: {title}")

                    else:
                        # UPDATE (do not touch abstract)
                        paper_id = row[0]
                        cursor.execute(
                            """
                            UPDATE papers
                            SET authors = ?, conference = ?, year = ?, paper_url = ?, topic = ?, keywords = ?
                            WHERE id = ?
                            """,
                            (
                                e["authors"], e["conference"], e["year"],
                                e["paper_url"], e["topic"], e["keywords"], paper_id
                            )
                        )
                        count_updated += 1
                        logging.info(f"[SAVE][{idx}] Updated: {title}")

                except Exception as entry_err:
                    logging.error(f"[SAVE][{idx}] Skipped entry due to error: {entry_err}")
                    skipped_entries.append({"index": idx, "title": entry["title"], "error": str(entry_err)})

            conn.commit()

        msg = f"Inserted {count_inserted}, updated {count_updated} papers to {paper_db_path}."
        data = {
            "path": paper_db_path,
            "inserted": count_inserted,
            "updated": count_updated,
            "skipped": len(skipped_entries),
        }

        if len(skipped_entries) > 0:
            status = 'warning'
            # msg += f"Failed inserting {len(skipped_entries)} papers: {skipped_entries}"
            msg = f"{msg} Failed inserting {len(skipped_entries)} papers."
        else:
            if (count_inserted + count_updated) > 0:
                status = 'success'
            else:
                status = 'warning'
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
    init_resp = data_process.initialize_paper_database(paper_db_path)
    if init_resp.get("status") == "error":
        msg = f"Cannot initialize database: {init_resp.get('message')}"
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
                WHERE title = ?
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
    Filter papers for a conference/year by title keywords and/or topic membership (no abstract).
    
    Args:
        conference (str): Conference name.
        year (int): Conference year.
        topic_keywords (TopicKeywordsModel): Object with .topic and .keywords.
        paper_db_path (str): Path to the SQLite database file.
    """
    # Ensure table exists
    init_resp = data_process.initialize_paper_database(paper_db_path)
    if init_resp.get("status") == "error":
        msg = f"Cannot initialize database: {init_resp.get('message')}"
        logging.error(f"[FILTER][INIT] {msg}")
        return helper_func.make_response("error", msg, None)

    failed_entries: List[Dict[str, Any]] = []

    # Normalize inputs
    topic_str = (getattr(topic_keywords, "topic", "") or "").strip()
    keywords_in: List[str] = [k for k in getattr(topic_keywords, "keywords", []) if isinstance(k, str)]
    keywords_set = {k.lower().strip() for k in keywords_in if k.strip()}

    if not topic_str and not keywords_set:
        msg = "No topic or keywords provided."
        logging.warning(f"[FILTER] {msg}")
        return helper_func.make_response(
            "warning",
            msg,
            {
                "conference": conference,
                "year": year,
                "filtered_count": 0,
                "papers": [],
                "failed_entries": [],
            },
        )
    
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT
                    title,       -- 0
                    authors,     -- 1 (JSON)
                    conference,  -- 2
                    year,        -- 3
                    paper_url,   -- 4
                    topic,       -- 5 (JSON)
                    keywords     -- 6 (JSON)
                FROM papers
                WHERE conference=? AND year=?
            """
            params = [conference, year]

             # --- DB query with explicit error handling ---
            try:  
                cursor.execute(query, params)  
                rows = cursor.fetchall()  

            except sqlite3.Error as db_err:     
                msg = f"Failed to fetch papers from database {paper_db_path}: {db_err}"  
                logging.exception(f"[FILTER] {msg}")  
                return helper_func.make_response("error", msg, None)  
            
            except Exception as db_err:         
                msg = f"Unexpected DB error: {db_err}"  
                logging.exception(f"[FILTER] {msg}")    
                return helper_func.make_response("error", msg, None)  

            logging.info(f"[FILTER] Fetched {len(rows)} papers from {paper_db_path} for {conference} {year}")

            # If no rows found, return a warning early
            if len(rows) == 0:  # NEW
                msg = f"No papers found for {conference} {year}."  # NEW
                logging.warning(f"[FILTER] {msg}")  # NEW
                return helper_func.make_response(   # NEW
                    "warning",
                    msg,
                    {
                        "conference": conference,
                        "year": year,
                        "filtered_count": 0,
                        "papers": [],
                        "failed_entries": [],
                        "save_result": helper_func.make_response("warning", "No papers to update.", None),
                    },
                )

        filtered_papers: List[Dict[str, Any]] = []

        for idx, row in enumerate(rows):
            try:
                # Parse JSON columns
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

                # Matching
                title_lc = (paper["title"] or "").lower()
                in_title = bool(keywords_set) and any(kw in title_lc for kw in keywords_set)

                topic_db_lc = [t.lower() for t in paper["topic"] if isinstance(t, str)]
                in_topic = bool(topic_str) and (topic_str.lower() in topic_db_lc)

                db_keywords_lc = {k.lower() for k in paper["keywords"] if isinstance(k, str)}
                in_db_keywords = bool(keywords_set) and bool(db_keywords_lc & keywords_set)

                if in_title or in_topic or in_db_keywords:
                    filtered_papers.append(paper)

            except Exception as parse_err:
                logging.error(f"[FILTER][{idx}] Error parsing row: {parse_err}")
                failed_entries.append({
                    "index": idx,
                    "row_data": list(row),
                    "error": str(parse_err),
                })

        logging.info(f"[FILTER] {len(filtered_papers)} papers matched for {conference} {year}.")
            
        # Prepare updates: merge topic (single string) and keywords (list)
        updated_paper_info_list: List[Dict[str, Any]] = []
        for idx, paper in enumerate(filtered_papers):
            try:
                updated_entry = dict(paper)
                topic_list_from_input = [topic_str] if topic_str else []
                updated_entry["topic"] = helper_func.merge_unique_elements(
                    paper.get("topic", []),
                    topic_list_from_input
                )
                updated_entry["keywords"] = helper_func.merge_unique_elements(
                    paper.get("keywords", []),
                    list(keywords_set)  # keep the provided ones
                )
                updated_paper_info_list.append(updated_entry)
                logging.info(f"[FILTER][{idx}] Merged topic/keywords for '{paper['title']}'")
            except Exception as merge_err:
                logging.error(f"[FILTER][{idx}] Error merging topic/keywords: {merge_err}")
                failed_entries.append({
                    "index": idx,
                    "title": paper.get("title"),
                    "error": str(merge_err),
                })

        # Persist updates if any
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

        status = "success"
        msg = f"Filtered {len(filtered_papers)} papers for {conference} {year}."
        if save_result.get("status") == "error":
            status = "error"
            msg = f"{msg} Failed to save the update oaoers."
        elif len(filtered_papers) == 0:
            status = "warning"
            msg = f"{msg} No new paper updates for this topic."
        elif len(failed_entries) > 0:
            status = "warning"
            msg = f"{msg} Failed updating topic and keywords info for {len(failed_entries)} papers."

        return helper_func.make_response(
            status,
            msg,
            {
                "conference": conference,
                "year": year,
                "filtered_count": len(filtered_papers),
                "papers": filtered_papers,
                "failed_entries": failed_entries,
                "save_result": save_result,
            },
        )

    except sqlite3.Error as db_err:
        msg = f"Failed to fetch papers from database {paper_db_path}: {db_err}"
        logging.exception(f"[FILTER] {msg}")
        return helper_func.make_response("error", msg, None)
    except Exception as e:
        msg = f"Failed to filter and update papers: {e}"
        logging.exception(f"[FILTER] {msg}")
        return helper_func.make_response("error", msg, None)

class FetchPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

def fetch_paper_list(
    conference: str,
    year: int,
    paper_db_path: str
) -> Dict[str, Any]:
    try:
        # Use your actual fetcher, this is a stub example
        if conference.lower() in ['nips', 'neurips']:
            papers = paper_crawler.fetch_neurips_papers(year)
            result = save_paper_info(papers, conference, year, paper_db_path)
            if "error" not in result.keys():
                logging.info(f"[FETCH] Fetched and saved papers for {conference} {year}")
                return {"message": f"Fetched and saved {len(papers)} papers for {conference} {year}"}
            else:
                logging.error(f"[Fail] Failed to fetch  papers for {conference} {year}")
                return {"error": f"Failed to fetch paper {conference} {year}, {result['error']}"}

        else:
            logging.warning(f"[FETCH] Crawling not supported for {conference}")
            return {"error": f"Crawling not supported for {conference}"}
    except Exception as e:
        logging.exception("[FETCH] Exception during fetching paper list")
        return {"error": f"Failed to fetch papers: {str(e)}"}
    
class GenerateKeywordListArgs(BaseModel):
    topic: str = Field(..., description="The research topic or subject to generate keywords for, for instance ['privacy'].")

def generate_keyword_list(
        topic: str, 
        llm,
        instruction) -> dict:
    """
    Generate keywords for a topic using an LLM with few-shot prompt.
    On parsing error, returns a dict with an 'error' key and the raw response.
    """
    if llm is None:
        logging.error("[KEYWORD_GEN] No LLM provided for topic '%s'.", topic)
        return {"error": "No LLM provided to generate keywords.", "topic": topic}

    prompt = f"""{instruction}

Now, do the same for this topic:
Topic: "{topic}"
Output:
    """

    try:
        logging.info(f"[KEYWORD_GEN] Sending prompt to LLM for topic: '{topic}'")
        response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        response_text = response.content if hasattr(response, "content") else response
        cleaned_text = data_process.strip_code_block(response_text)
        logging.info(f"[KEYWORD_GEN] Raw LLM response: {response_text[:200]}")
        
        # Try JSON first, then fallback to ast.literal_eval
        try:
            result = json.loads(cleaned_text)
            logging.info("[KEYWORD_GEN] Successfully parsed LLM output as JSON.")
        except Exception as json_err:
            logging.warning(f"[KEYWORD_GEN] JSON parsing failed: {json_err}, trying ast.literal_eval...")
            try:
                result = ast.literal_eval(cleaned_text)
                logging.info("[KEYWORD_GEN] Successfully parsed LLM output with ast.literal_eval.")
            except Exception as ast_err:
                logging.error(f"[KEYWORD_GEN] Both JSON and ast parsing failed. ast error: {ast_err}")
                return {
                    "error": f"Failed to parse LLM output as JSON or Python: {ast_err}",
                    "raw_response": response_text[:500],
                }

        # Post-processing & validation
        if (
            isinstance(result, dict)
            and "topic" in result and isinstance(result["topic"], str)
            and "keywords" in result and isinstance(result["keywords"], list)
        ):
            topic_val = result["topic"].strip().lower()
            keywords_list = [k.strip().lower() for k in data_process.ensure_list(result["keywords"])]

            logging.info(f"[KEYWORD_GEN] Extracted topic: {topic_val}, keywords: {keywords_list}")

            return {
                "message": f"Extracted: {topic_val}, keywords: {keywords_list}",
                "topic": topic_val,
                "keywords": keywords_list
            }
        else:
            logging.error(f"[KEYWORD_GEN] LLM output not in expected dict structure: {result}")
            return {
                "error": "Output did not match expected dict structure, topic to be string and keyword to be lists.",
                "raw_response": response_text[:500],
            }
    except Exception as e:
        logging.exception(f"[KEYWORD_GEN] Exception during LLM keyword generation for topic '{topic}'")
        return {
            "error": f"Could not parse LLM output: {e}",
            "raw_response": str(response_text)[:500] if 'response_text' in locals() else ""
        }



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
    func=partial(generate_keyword_list, llm=llm_provider.get_llm(config), instruction=prompts.keyword_generation_prompt),
    args_schema=GenerateKeywordListArgs,
    name="generate_keyword_list_given_topic",
    description="Given a research topic or concept, generate a list of keywords using an LLM."
)


paper_fetch_toolkit = [
    # save_paper_tool,
    get_paper_info_tool,
    fetch_paper_list_tool,
    filter_paper_by_topic_tool,
    keyword_generation_tool
]
