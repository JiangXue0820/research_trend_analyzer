from typing import Optional, List, Dict, Any
import os
import json
import requests
from tqdm import tqdm
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
import logging

import sys
sys.path.append("../")
from utils.paper_crawler import *
from configs import config
from configs.logging import configure_logging
from configs.llm_provider import get_llm

# --------------------- LOGGING ------------------------

configure_logging()
# ------------------- DATA TYPES -----------------------

class TopicKeywordsModel(BaseModel):
    topic: str
    keywords: List[str]

# ---------- 1) Raw Functions ----------

def save_paper_info(
    paper_info_list: List[Dict[str, Any]],
    conference: str,
    year: int,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> Dict[str, Any]:
    """
    Save a list of paper metadata dictionaries to a JSONL file.
    Returns a dict with the file path and number of papers saved.
    """
    topic_suffix = f"_{topic_keywords.topic}" if topic_keywords and topic_keywords.topic else ''
    conf = conference.lower()
    filename = f"{conf}{year}{topic_suffix}.jsonl"
    dirpath = os.path.join("paper_list", conf)
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, filename)

    # Append JSONL entries
    with open(filepath, 'a', encoding='utf-8') as f:
        for entry in paper_info_list:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    logging.info(f"Saved {len(paper_info_list)} papers to {filepath}")
    return {"filepath": filepath, "total_count": len(paper_info_list)}

def load_paper_list(
    conference: str,
    year: int,
    topic_keywords: Optional[TopicKeywordsModel] = None
) -> List[Dict[str, Any]]:
    """
    Load paper metadata from JSONL file for a given conference/year.
    Returns an empty list if file does not exist.
    """
    topic_suffix = f"_{topic_keywords.topic}" if topic_keywords and topic_keywords.topic else ''
    conf = conference.lower()
    filepath = os.path.join("paper_list", conf, f"{conf}{year}{topic_suffix}.jsonl")

    if not os.path.exists(filepath):
        logging.info(f"No paper list found at {filepath}. Returning empty list.")
        return []

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
    return papers

def filter_paper_by_topic(
    conference: str,
    year: int,
    topic_keywords: TopicKeywordsModel
) -> Dict[str, Any]:
    """
    Filter the master list by topic keywords and save to a topic-specific file.
    Returns a dict with the filtered file path and number of papers.
    """
    conf = conference.lower()
    master_file = os.path.join("paper_list", conf, f"{conf}{year}.jsonl")
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
                if meta and paper_matches_topic(meta, keywords):
                    filtered.append(meta)
    except Exception as e:
        logging.error(f"Error reading {master_file}: {e}")
        return {"error": f"Error reading {master_file}: {e}"}
    
    unique_filtered = [meta for meta in filtered if meta.get('paper_url') and meta.get('paper_url') not in seen_urls]

    result = save_paper_info(unique_filtered, conference, year, topic_keywords)
    result.update({"total_count": len(unique_filtered)+len(existing)})
    result.update({"new_count": len(unique_filtered)})
    return result


def fetch_paper_list(
    conference: str,
    year: int
) -> Dict[str, Any]:
    """
    Fetch all papers for a conference/year, dedupe by URL, and save new entries.
    Returns a dict with the file path and number of new papers.
    """
    conf = conference.lower()
    dirpath = os.path.join("paper_list", conf)
    os.makedirs(dirpath, exist_ok=True)
    existing = load_paper_list(conference, year)
    seen_urls = {p.get('paper_url') for p in existing if p.get('paper_url')}

    if conf in ['nips', 'neurips']:
        all_metas = fetch_neurips_papers(year)
    else:
        return {"error": f"Crawling not supported for conference '{conference}'"}

    if all_metas is None:
        return {"error": "Failed to fetch paper list."}
    
    new_metas = [meta for meta in all_metas if meta.get('paper_url') and meta.get('paper_url') not in seen_urls]

    result = save_paper_info(new_metas, conference, year)
    result.update({"total_count": len(new_metas)+len(existing)})
    result.update({"new_count": len(new_metas)})
    return result

    
def generate_keyword_list(topic: str, llm=None) -> dict:
    """
    Generate keywords for a topic using an LLM with few-shot prompt.
    On parsing error, returns a dict with an 'error' key and the raw response.
    """
    if llm is None:
        return {"error": "No LLM provided to generate keywords.", "topic": topic}

    prompt = f"""
You are an assistant that helps generate comprehensive keyword lists for academic research topics.
Given a topic, output a Python dict: {{"topic": ..., "keywords": [...]}}. 
The 'keywords' list should include at least 10 relevant items:
- Include the verb/noun/adjective forms, common phrases, technical terms, subfields, related concepts, and typical synonyms or abbreviations.
- Try to cover both core and popular subtopics.
- Output strictly as a Python dict (see examples).
Rethink: Are there any important related keywords or subtopics missing? If yes, please output an updated list with the additions.

Example 1:
Topic: "privacy"
Output: {{"topic": "privacy", "keywords": ["privacy", "private", "anonymity", "anonymous", "data protection", "federated learning"]}}

Example 2:
Topic: "safety"
Output: {{"topic": "safety", "keywords": ["safety", "safe", "safety alignment", "robustness", "risk assessment", "safety risk"]}}

Example 3:
Topic: "attack"
Output: {{"topic": "attack", "keywords": ["attack", "membership inference", "model inversion", "memorization", "backdoor", "jailbreak", "red-team", "poison"]}}      

Now, do the same for this topic:
Topic: "{topic}"
Output:
    """

    response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
    response_text = response.content if hasattr(response, "content") else response

    import ast
    try:
        result = ast.literal_eval(response_text.strip())
        if (
            isinstance(result, dict) and
            "topic" in result and
            isinstance(result.get("keywords"), list)
        ):
            result["keywords"] = [k.strip() for k in result["keywords"]]
            return result
    except Exception as e:
        return {
            "error": f"Could not parse LLM output: {e}",
            "raw_response": response_text,
            "topic": topic
        }

    # fallback shouldn't trigger, as exception will catch all, but here as extra safety
    return {
        "error": "Unknown error in parsing LLM output.",
        "raw_response": response_text,
        "topic": topic
    }


# ---------- 2) Pydantic Schemas ----------

class SavePaperArgs(BaseModel):
    paper_info_list: List[Dict[str, Any]] = Field(..., description="List of paper metadata dicts")
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

class LoadPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: Optional[TopicKeywordsModel] = Field(default=None, description="Dict with keys 'topic' and 'keywords' (optional).")

class FilterPaperByTopicArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")
    topic_keywords: TopicKeywordsModel = Field(..., description="Dict with keys 'topic' and 'keywords' (required).")

class FetchPaperArgs(BaseModel):
    conference: str = Field(..., description="Conference name")
    year: int = Field(..., description="Year")

class GenerateKeywordListArgs(BaseModel):
    topic: str = Field(..., description="The research topic or subject to generate keywords for.")


# ---------- 3) LangChain Structured Tools ----------

save_paper_tool = StructuredTool.from_function(
    func=save_paper_info,
    args_schema=SavePaperArgs,
    name="save_paper_info",
    description="Save a list of paper metadata (title, authors, abstract, urls) to a JSONL file under paper_list/<conference>/<conference><year>.jsonl. Optionally grouped by topic."
)

load_paper_tool = StructuredTool.from_function(
    func=load_paper_list,
    args_schema=LoadPaperArgs,
    name="load_paper_list",
    description="Load paper metadata from the JSONL file saved by save_paper_info for a given conference and year. Optionally load a topic-filtered file."
)

filter_paper_by_topic_tool = StructuredTool.from_function(
    func=filter_paper_by_topic,
    args_schema=FilterPaperByTopicArgs,
    name="filter_paper_by_topic",
    description="Filter a conference/year's paper list JSONL file by a topic's keywords, saving the filtered list to a topic-specific file. Returns file path and number of filtered papers."
)

fetch_paper_list_tool = StructuredTool.from_function(
    func=fetch_paper_list,
    args_schema=FetchPaperArgs,
    name="fetch_paper_list",
    description="Fetch all papers from a given conference and year from conference website, dedupe existing, and save new to JSONL."
)

# 这里 generate_keyword_list 需要注意，如果你的函数签名是 (topic: str, llm=None)，
# LangChain只会传 schema 字段（即 topic），你可以用 partial 或包装函数
from functools import partial
keyword_generation_tool = StructuredTool.from_function(
    func=partial(generate_keyword_list, llm=get_llm(config)),
    args_schema=GenerateKeywordListArgs,
    name="generate_keyword_list_given_topic",
    description="Given a research topic or concept, generate a list of keywords using an LLM."
)

# ---------- 4) Toolkit ----------

data_fetch_toolkit = [
    save_paper_tool,
    load_paper_tool,
    fetch_paper_list_tool,
    keyword_generation_tool,
    filter_paper_by_topic_tool  
]