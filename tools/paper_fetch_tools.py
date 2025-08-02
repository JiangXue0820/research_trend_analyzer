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

import sys
sys.path.append("../")
from utils import prompts, paper_crawler
from configs import config
from configs.logging import configure_logging
from configs.llm_provider import get_llm

# --------------------- LOGGING ------------------------

configure_logging()
# ------------------- DATA TYPES -----------------------

class TopicKeywordsModel(BaseModel):
    topic: str
    keywords: List[str]

# ---------- 1) Save Papaer Tool ----------

class SavePaperArgs(BaseModel):
    paper_info_list: List[Dict[str, Any]] = Field(..., description="List of paper metadata dicts")
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

def save_paper_info(
    paper_info_list: List[Dict[str, Any]],
    conference: str,
    year: int,
    paper_list_path,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> Dict[str, Any]:
    """
    Save a list of paper metadata dictionaries to a JSONL file.
    Returns a dict with the file path and number of papers saved.
    """
    topic_suffix = f"_{topic_keywords.topic}" if topic_keywords and topic_keywords.topic else ''
    conf = conference.lower()
    filename = f"{conf}{year}{topic_suffix}.jsonl"
    dirpath = os.path.join(paper_list_path, conf)
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, filename)

    # Append JSONL entries
    with open(filepath, 'a', encoding='utf-8') as f:
        for entry in paper_info_list:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    logging.info(f"Saved {len(paper_info_list)} papers to {filepath}")
    return {"filepath": filepath, "total_count": len(paper_info_list)}

save_paper_tool = StructuredTool.from_function(
    func=partial(save_paper_info, paper_list_path=config.PAPER_LIST_PATH),
    args_schema=SavePaperArgs,
    name="save_paper_info",
    description="Save a list of paper metadata (title, authors, abstract, urls) to a JSONL file under paper_list/<conference>/<conference><year>.jsonl. Optionally grouped by topic."
)

# ---------- 2) Load Papaer Tool ----------

class LoadPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

def load_paper_list(
    conference: str,
    year: int,
    paper_list_path,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> Dict[str, Any]:
    """
    Load paper metadata from JSONL file for a given conference/year.
    """
    topic_suffix = f"_{topic_keywords.topic}" if topic_keywords and topic_keywords.topic else ''
    conf = conference.lower()
    filepath = os.path.join(paper_list_path, conf, f"{conf}{year}{topic_suffix}.jsonl")

    if not os.path.exists(filepath):
        logging.info(f"No paper list found at {filepath}. Returning empty list.")
        return {"error": f"No paper list found at {filepath}. Returning empty list."}

    papers: List[Dict[str, Any]] = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                logging.warning(f"Skipping invalid JSON line in {filepath}")
    return {"papers": papers}

load_paper_tool = StructuredTool.from_function(
    func=partial(load_paper_list, paper_list_path=config.PAPER_LIST_PATH),
    args_schema=LoadPaperArgs,
    name="load_paper_list",
    description="Load paper metadata from the JSONL file saved by save_paper_info for a given conference and year. Optionally load a topic-filtered file."
)

# ---------- 3) Filter Papaer Tool ----------

class FilterPaperByTopicArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: TopicKeywordsModel = Field(..., description="Dict with keys 'topic' and 'keywords' (required).")

def filter_paper_by_topic(
    conference: str,
    year: int,
    topic_keywords: TopicKeywordsModel,
    paper_list_path
) -> Dict[str, Any]:
    """
    Filter the master list by topic keywords and save to a topic-specific file.
    Returns a dict with the filtered file path and number of papers.
    """
    conf = conference.lower()
    master_file = os.path.join(paper_list_path, conf, f"{conf}{year}.jsonl")
    if not os.path.exists(master_file):
        logging.error(f"Master paper list not found: {master_file}")
        return {"error": f"Master paper list not found: {master_file}"}

    topic = topic_keywords.topic
    keywords = topic_keywords.keywords
    if not keywords or not topic:
        logging.error("Keywords or topic is empty")
        return {"error": "Keywords or topic is empty"}
    
    existing = load_paper_list(conference, year, topic_keywords)
    seen_urls = {p.get('paper_url') for p in existing if p.get('paper_url')}
    
    filtered: List[Dict[str, Any]] = []

    try:
        with open(master_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    meta = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if meta and paper_crawler.paper_matches_topic(meta, keywords):
                    filtered.append(meta)
    except Exception as e:
        logging.error(f"Error reading {master_file}: {e}")
        return {"error": f"Error reading {master_file}: {e}"}
    
    unique_filtered = [meta for meta in filtered if meta.get('paper_url') and meta.get('paper_url') not in seen_urls]

    result = save_paper_info(unique_filtered, conference, year, topic_keywords)
    result.update({"total_count": len(unique_filtered)+len(existing)})
    result.update({"new_count": len(unique_filtered)})
    return result

filter_paper_by_topic_tool = StructuredTool.from_function(
    func=partial(filter_paper_by_topic, paper_list_path=config.PAPER_LIST_PATH),
    args_schema=FilterPaperByTopicArgs,
    name="filter_paper_by_topic",
    description="Filter a conference/year's paper list JSONL file by a topic's keywords, saving the filtered list to a topic-specific file. Returns file path and number of filtered papers."
)

# ---------- 4) Fetch Papaer List Tool ----------

class FetchPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

def fetch_paper_list(
    conference: str,
    year: int,
    paper_list_path
) -> Dict[str, Any]:
    """
    Fetch all papers for a conference/year, dedupe by URL, and save new entries.
    Returns a dict with the file path and number of new papers.
    """
    dirpath = os.path.join(paper_list_path, conference.lower())
    os.makedirs(dirpath, exist_ok=True)
    existing = load_paper_list(conference, year)
    seen_urls = {p.get('paper_url') for p in existing if p.get('paper_url')}

    if conference.lower() in ['nips', 'neurips']:
        all_metas = paper_crawler.fetch_neurips_papers(year)
    else:
        return {"error": f"Crawling not supported for conference '{conference}'"}

    if all_metas is None:
        return {"error": "Failed to fetch paper list."}
    new_metas = [meta for meta in all_metas if meta.get('paper_url') and meta.get('paper_url') not in seen_urls]

    result = save_paper_info(new_metas, conference, year)
    result.update({"total_count": len(new_metas)+len(existing)})
    result.update({"new_count": len(new_metas)})
    return result

fetch_paper_list_tool = StructuredTool.from_function(
    func=partial(fetch_paper_list, paper_list_path=config.PAPER_LIST_PATH),
    args_schema=FetchPaperArgs,
    name="fetch_paper_list",
    description="Fetch all papers from a given conference and year from conference website, dedupe existing, and save new to JSONL."
)

# ---------- 5) Generate Keyword Tool ----------
class GenerateKeywordListArgs(BaseModel):
    topic: str = Field(..., description="The research topic or subject to generate keywords for.")
    
def generate_keyword_list(
        topic: str, 
        llm,
        instruction) -> dict:
    """
    Generate keywords for a topic using an LLM with few-shot prompt.
    On parsing error, returns a dict with an 'error' key and the raw response.
    """
    if llm is None:
        return {"error": "No LLM provided to generate keywords.", "topic": topic}

    prompt = f"""{instruction}

Now, do the same for this topic:
Topic: "{topic}"
Output:
    """

    response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
    response_text = response.content if hasattr(response, "content") else response

    try:
        response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
        response_text = response.content if hasattr(response, "content") else response

        result = ast.literal_eval(response_text.strip())
        if (
            isinstance(result, dict)
            and "topic" in result
            and isinstance(result.get("keywords"), list)
        ):
            result["keywords"] = [k.strip() for k in result["keywords"]]
            return result
        else:
            return {
                "error": "Output did not match expected dict structure.",
                "topic": topic,
                "raw_response": response_text[:500],
            }
    except Exception as e:
        return {
            "error": f"Could not parse LLM output: {e}",
            "topic": topic,
            "raw_response": str(response_text)[:500],
        }

# 这里 generate_keyword_list 需要注意，如果你的函数签名是 (topic: str, llm=None)，
# LangChain只会传 schema 字段（即 topic），你可以用 partial 或包装函数
keyword_generation_tool = StructuredTool.from_function(
    func=partial(generate_keyword_list, llm=get_llm(config), instruction=prompts.keyword_generation_prompt),
    args_schema=GenerateKeywordListArgs,
    name="generate_keyword_list_given_topic",
    description="Given a research topic or concept, generate a list of keywords using an LLM."
)

# ---------- 6) Toolkit ----------

paper_fetch_toolkit = [
    save_paper_tool,
    load_paper_tool,
    fetch_paper_list_tool,
    keyword_generation_tool,
    filter_paper_by_topic_tool  
]