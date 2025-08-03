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
from utils import paper_crawler, prompts, data_process
from configs import config, llm_provider


class TopicKeywordsModel(BaseModel):
    topic: str = Field(..., description="Topic of papers")
    keywords: List[str] = Field(..., description="List of keywords of a certain topic")

class SavePaperArgs(BaseModel):
    paper_info_list: List[Dict[str, Any]] = Field(..., description="List of paper metadata dicts")
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

def save_paper_info_sql(
    paper_info_list: List[Dict[str, Any]],
    conference: str,
    year: int,
    paper_db_path: str,
) -> Dict[str, Any]:

    result = data_process.initialize_paper_database(paper_db_path)
    if "error" in result.keys():
        return {"error": f"[INIT] Fail to initialize database: {result['error']}"}
    logging.info(f"[INIT] Checked/initialized database at {paper_db_path}")

    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        count_inserted = 0
        count_updated = 0

        skipped_entries = []
        for idx, entry in enumerate(paper_info_list):
            try:
                entry = entry.copy()
                title = entry.get("title")
                if not title:
                    logging.error(f"[SAVE][{idx}] Paper entry missing 'title'; skipping entry: {entry}")
                    skipped_entries.append({"index": idx, "entry": entry, "error": "Paper entry missing 'title'"})
                    continue

                entry["conference"] = str(conference)
                entry["year"] = int(year)

                entry["topic"] = json.dumps(data_process.ensure_list(entry.get("topic", [])))
                entry["keywords"] = json.dumps(data_process.ensure_list(entry.get("keywords", [])))
                entry["authors"] = json.dumps(data_process.ensure_list(entry.get("authors", [])))
                entry["paper_url"] = str(entry.get("paper_url", ""))
                entry.setdefault("abstract", None)

                cursor.execute("SELECT id FROM papers WHERE title = ?", (title,))
                row = cursor.fetchone()

                if row is None:
                    cursor.execute('''
                        INSERT INTO papers (title, authors, abstract, conference, year, paper_url, topic, keywords)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        entry["title"], entry["authors"], entry["abstract"], entry["conference"], entry["year"],
                        entry["paper_url"], entry["topic"], entry["keywords"]
                    ))
                    count_inserted += 1
                    logging.info(f"[SAVE][{idx}] Inserted new paper: {title}")
                else:
                    paper_id = row[0]
                    cursor.execute(
                        '''
                        UPDATE papers
                        SET authors = ?, abstract = ?, conference = ?, year = ?, paper_url = ?, topic = ?, keywords = ?
                        WHERE id = ?
                        ''',
                        (
                            entry["authors"], entry["abstract"], entry["conference"], entry["year"],
                            entry["paper_url"], entry["topic"], entry["keywords"], paper_id
                        )
                    )
                    count_updated += 1
                    logging.info(f"[SAVE][{idx}] Updated paper: {title}")

            except Exception as entry_err:
                logging.error(f"[SAVE][{idx}] Exception processing entry: {entry_err}")
                skipped_entries.append({"index": idx, "entry": entry, "error": str(entry_err)})

        conn.commit()
        conn.close()
        msg = f"Inserted {count_inserted}, updated {count_updated} papers to {paper_db_path}"
        logging.info(f"[SAVE] {msg}")
        result = {"message": msg}
        if skipped_entries:
            result["skipped_entries"] = skipped_entries
        return result
    except Exception as e:
        logging.exception("[SAVE] Exception during saving paper info")
        return {"error": f"Failed to save paper info: {str(e)}"}


class LoadPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

def load_paper_list_sql(
    paper_db_path: str,
    title: Optional[str] = None,
    conference: Optional[str] = None,
    year: Optional[int] = None,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> Dict[str, Any]:
    """
    Load papers from SQL database by:
      - title (if provided), OR
      - conference + year (optionally filter by topic overlap in Python)
    """
    # Always ensure the table exists
    data_process.initialize_paper_database(paper_db_path)

    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        papers = []

        if title:
            query = """
                SELECT title, authors, abstract, conference, year, paper_url, topic, keywords 
                FROM papers 
                WHERE title = ?
            """
            params = [title]
            logging.info(f"[LOAD] Loading by title: {title}")
        elif conference and year:
            query = """
                SELECT title, authors, abstract, conference, year, paper_url, topic, keywords 
                FROM papers 
                WHERE conference = ? AND year = ?
            """
            params = [conference, year]
            logging.info(f"[LOAD] Loading by conference={conference}, year={year}")
        else:
            return {"error": "Must provide either title, or conference+year (optionally topic)."}

        cursor.execute(query, params)
        for row in cursor.fetchall():
            paper = {
                "title": row[0],
                "authors": json.loads(row[1]) if row[1] else [],
                "abstract": row[2],
                "conference": row[3],
                "year": row[4],
                "paper_url": row[5],
                "topic": json.loads(row[6]) if row[6] else [],
                "keywords": json.loads(row[7]) if row[7] else [],
            }
            papers.append(paper)
        conn.close()

        # Topic overlap filtering (in Python), if needed
        if conference and year and topic_keywords and topic_keywords.keywords:
            keywords_set = set(t.lower() for t in topic_keywords.keywords)
            filtered_papers = []
            for paper in papers:
                paper_keywords = set(t.lower() for t in paper.get("keywords", []))
                if paper_keywords & keywords_set:
                    filtered_papers.append(paper)
            papers = filtered_papers
            logging.info(f"[LOAD] After topic overlap filtering: {len(papers)} papers")

        logging.info(f"[LOAD] Loaded {len(papers)} papers.")

        # Check for ambiguity in title query
        if title and len(papers) != 1:
            logging.warning(f"[LOAD] Loaded more than one paper with name '{title}'.")
            return {
                "message": f"Loaded more than one paper with name '{title}'.",
                "papers": papers
            }
        return {
            "message": f"[LOAD] Loaded {len(papers)} papers.",
            "papers": papers
        }
    except Exception as e:
        logging.exception("[LOAD] Exception during loading paper info")
        return {"error": f"Failed to load paper info: {str(e)}"}


class FilterPaperByTopicArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: TopicKeywordsModel = Field(..., description="Dict with keys 'topic' and 'keywords' (required).")

def filter_paper_by_topic_sql(
    conference: str,
    year: int,
    topic_keywords: TopicKeywordsModel,
    paper_db_path: str
) -> Dict[str, Any]:
    
    # Always ensure the table exists
    data_process.initialize_paper_database(paper_db_path)

    failed_entries = []
    try:
        with sqlite3.connect(paper_db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT title, authors, abstract, conference, year, paper_url, topic, keywords
                FROM papers
                WHERE conference=? AND year=?
            """
            params = [conference, year]
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                logging.info(f"[FILTER] Fetched {len(rows)} papers from database {paper_db_path} for {conference} {year}")
            except Exception as db_err:
                logging.exception(f"[FILTER] Failed to fetch papers from database {paper_db_path}: {db_err}")
                return {"error": f"Failed to fetch papers from database {paper_db_path}: {db_err}"}

            keywords_set = set(kw.lower() for kw in topic_keywords.keywords if isinstance(kw, str))
            filtered_papers = []
            for idx, row in enumerate(rows):
                try:
                    paper = {
                        "title": row[0],
                        "authors": json.loads(row[1]) if row[1] else [],
                        "abstract": row[2] or "",
                        "conference": row[3],
                        "year": row[4],
                        "paper_url": row[5],
                        "topic": json.loads(row[6]) if row[6] else [],
                        "keywords": json.loads(row[7]) if row[7] else []
                    }
                    in_keywords = any(kw in paper["abstract"].lower() for kw in keywords_set)
                    in_title = any(kw in (paper["title"] or "").lower() for kw in keywords_set)
                    in_paper_keywords = set(k.lower() for k in paper["keywords"])
                    if in_keywords or in_title or keywords_set & in_paper_keywords:
                        filtered_papers.append(paper)
                except Exception as parse_err:
                    error_msg = f"[FILTER][{idx}] Error parsing row: {parse_err}"
                    logging.error(error_msg)
                    failed_entries.append({
                        "index": idx,
                        "row_data": list(row),
                        "error": str(error_msg)
                    })

            logging.info(f"[FILTER] {len(filtered_papers)} papers matched filter for {conference} {year} and keywords.")

            updated_paper_info_list = []
            for idx, paper in enumerate(filtered_papers):
                try:
                    updated_entry["topic"] = data_process.merge_unique_elements(paper["topic"], data_process.ensure_list(topic_keywords.topic))
                    updated_entry["keywords"] = data_process.merge_unique_elements(paper["keywords"], data_process.ensure_list(topic_keywords.keywords))
                    updated_entry = paper.copy()
                    updated_paper_info_list.append(updated_entry)
                    logging.debug(f"[FILTER][{idx}] Merged topics/keywords for '{paper['title']}'")
                except Exception as merge_err:
                    error_msg = f"[FILTER][{idx}] Error merging topics/keywords: {merge_err}"
                    logging.error(error_msg)
                    failed_entries.append({
                        "index": idx,
                        "title": paper.get("title"),
                        "error": str(error_msg)
                    })

            # Save updated papers
            if updated_paper_info_list:
                try:
                    save_result = save_paper_info_sql(
                        paper_info_list=updated_paper_info_list,
                        conference=conference,
                        year=year,
                        paper_db_path=paper_db_path
                    )
                    logging.info(f"[FILTER][UPDATE] Saved {len(updated_paper_info_list)} updated papers. Save result: {save_result}")
                except Exception as save_err:
                    logging.exception(f"[FILTER][UPDATE] Exception saving updated papers: {save_err}")
                    save_result = {"error": f"Failed to save updated papers: {save_err}"}
            else:
                logging.info("[FILTER][UPDATE] No papers to update.")
                save_result = {"message": "No papers to update."}

            result = {
                "message": f"Filtered {len(filtered_papers)} papers; paper saving result: {save_result}",
                "papers": filtered_papers
            }
            if failed_entries:
                result["failed_entries"] = failed_entries
            return result

    except Exception as e:
        logging.exception("[FILTER] Exception during filtering and updating paper info")
        return {"error": f"Failed to filter and update papers: {str(e)}"}


class FetchPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

def fetch_paper_list_sql(
    conference: str,
    year: int,
    paper_db_path: str
) -> Dict[str, Any]:
    try:
        # Use your actual fetcher, this is a stub example
        if conference.lower() in ['nips', 'neurips']:
            papers = paper_crawler.fetch_neurips_papers(year)
            result = save_paper_info_sql(papers, conference, year, paper_db_path)
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
        logging.debug(f"[KEYWORD_GEN] Raw LLM response: {response_text[:200]}")
        
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



save_paper_tool = StructuredTool.from_function(
    func=partial(save_paper_info_sql, paper_db_path=config.PAPER_DB_PATH),
    args_schema=SavePaperArgs,
    name="save_paper_info",
    description="Save a list of paper metadata (title, authors, abstract, urls) to the SQL database. Optionally grouped by topic."
)
load_paper_tool = StructuredTool.from_function(
    func=partial(load_paper_list_sql, paper_db_path=config.PAPER_DB_PATH),
    args_schema=LoadPaperArgs,
    name="load_paper_list",
    description="Load paper metadata from the SQL database for a given conference and year. Optionally filter by topic."
)
filter_paper_by_topic_tool = StructuredTool.from_function(
    func=partial(filter_paper_by_topic_sql, paper_db_path=config.PAPER_DB_PATH),
    args_schema=FilterPaperByTopicArgs,
    name="filter_paper_by_topic",
    description="Filter papers in the SQL database by a topic's keywords, for a conference and year."
)
fetch_paper_list_tool = StructuredTool.from_function(
    func=partial(fetch_paper_list_sql, paper_db_path=config.PAPER_DB_PATH),
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
    save_paper_tool,
    load_paper_tool,
    fetch_paper_list_tool,
    filter_paper_by_topic_tool,
    keyword_generation_tool
]
