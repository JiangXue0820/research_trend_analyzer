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
from utils import prompts, paper_crawler
from configs import config
from configs.logging import configure_logging
from configs.llm_provider import get_llm

def create_paper_table(paper_db_path: str):
    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                conference TEXT,
                year INTEGER,
                paper_url TEXT,
                topic TEXT,
                keywords TEXT
            );
        ''')
        conn.commit()
        conn.close()
        logging.info(f"Created or checked table in {paper_db_path}")
    except Exception as e:
        logging.error(f"[CREATE_TABLE] Failed to create/check table: {e}")

class TopicKeywordsModel(BaseModel):
    topic: str
    keywords: List[str]

class SavePaperArgs(BaseModel):
    paper_info_list: List[Dict[str, Any]] = Field(..., description="List of paper metadata dicts")
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

def save_paper_info_sql(
    paper_info_list: List[Dict[str, Any]],
    conference: str,
    year: int,
    paper_db_path: str,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        count = 0
        for entry in paper_info_list:
            entry = entry.copy()
            entry["conference"] = conference
            entry["year"] = year
            entry["topic"] = topic_keywords.topic if topic_keywords else entry.get("topic")
            entry["keywords"] = json.dumps(topic_keywords.keywords if topic_keywords else entry.get("keywords", []))
            if isinstance(entry.get("authors"), list):
                entry["authors"] = json.dumps(entry["authors"])
            for col in ['title', 'authors', 'abstract', 'conference', 'year', 'paper_url', 'topic', 'keywords']:
                entry.setdefault(col, None)
            cursor.execute('''
                INSERT INTO papers (title, authors, abstract, conference, year, paper_url, topic, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry["title"], entry["authors"], entry.get("abstract"), entry["conference"], entry["year"],
                entry.get("paper_url"), entry["topic"], entry["keywords"]
            ))
            count += 1
        conn.commit()
        conn.close()
        logging.info(f"[SAVE] Saved {count} papers to {paper_db_path}")
        return {"message": f"Saved {count} papers to {paper_db_path}"}
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
      - conference + year (optionally topic)
    """
    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()

        papers = []

        if title:
            query = "SELECT title, authors, abstract, conference, year, paper_url, topic, keywords FROM papers WHERE title = ?"
            params = [title]
            logging.info(f"[LOAD] Loading by title: {title}")
        elif conference and year:
            query = "SELECT title, authors, abstract, conference, year, paper_url, topic, keywords FROM papers WHERE conference = ? AND year = ?"
            params = [conference, year]
            if topic_keywords and topic_keywords.topic:
                query += " AND topic = ?"
                params.append(topic_keywords.topic)
            logging.info(f"[LOAD] Loading by conference={conference}, year={year}, topic={getattr(topic_keywords, 'topic', None)}")
        else:
            return {"error": "Must provide either title, or conference+year (optionally topic)."}

        cursor.execute(query, params)
        for row in cursor.fetchall():
            papers.append({
                "title": row[0],
                "authors": json.loads(row[1]) if row[1] else [],
                "abstract": row[2],
                "conference": row[3],
                "year": row[4],
                "paper_url": row[5],
                "topic": row[6],
                "keywords": json.loads(row[7]) if row[7] else []
            })
        conn.close()
        logging.info(f"[LOAD] Loaded {len(papers)} papers. {papers}")

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
    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        query = "SELECT title, authors, abstract, conference, year, paper_url, topic, keywords FROM papers WHERE conference=? AND year=?"
        params = [conference, year]
        cursor.execute(query, params)
        keywords_set = set([kw.lower() for kw in topic_keywords.keywords])
        filtered = []
        for row in cursor.fetchall():
            paper = {
                "title": row[0],
                "authors": json.loads(row[1]) if row[1] else [],
                "abstract": row[2] or "",
                "conference": row[3],
                "year": row[4],
                "paper_url": row[5],
                "topic": row[6],
                "keywords": json.loads(row[7]) if row[7] else []
            }
            # Match: in title/abstract/keywords
            in_keywords = any(kw in paper["abstract"].lower() for kw in keywords_set)
            in_title = any(kw in (paper["title"] or "").lower() for kw in keywords_set)
            in_paper_keywords = set([k.lower() for k in paper["keywords"]])
            if in_keywords or in_title or keywords_set & in_paper_keywords:
                filtered.append(paper)
        conn.close()
        logging.info(f"[FILTER] Filtered {len(filtered)} papers for topic {topic_keywords.topic} in {conference} {year}")
        return {
            "message": f"Filtered {len(filtered)} papers", 
            "papers": filtered
            }
    except Exception as e:
        logging.exception("[FILTER] Exception during filtering paper info")
        return {"error": f"Failed to filter papers: {str(e)}"}


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
        from utils.paper_crawler import fetch_neurips_papers
        if conference.lower() in ['nips', 'neurips']:
            papers = fetch_neurips_papers(year)
            result = save_paper_info_sql(papers, conference, year, paper_db_path)
            if "error" not in result.keys():
                logging.info(f"[FETCH] Fetched and saved papers for {conference} {year}")
                return {"message": f"Fetched and saved papers for {conference} {year}"}
            else:
                logging.error(f"[Fail] Failed to fetch  papers for {conference} {year}")
                return {"error": f"Failed to fetch paper {conference} {year}, {result["error"]}"}

        else:
            logging.warning(f"[FETCH] Crawling not supported for {conference}")
            return {"error": f"Crawling not supported for {conference}"}
    except Exception as e:
        logging.exception("[FETCH] Exception during fetching paper list")
        return {"error": f"Failed to fetch papers: {str(e)}"}
    

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

paper_fetch_toolkit = [
    save_paper_tool,
    load_paper_tool,
    fetch_paper_list_tool,
    filter_paper_by_topic_tool,
]
