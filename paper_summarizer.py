from typing import Any, Dict, List
import os
import json
from configs.log_config import configure_logging
import logging
from utils.prompts import PAPER_SUMMARY_PROMPT

class PaperSummarizer:
    def __init__(self, conference: str, year: int, llm: Any):
        self.conference = conference
        self.year = year
        self.llm = llm

    def load_paper_list(self, conference: str, year: int):
        """
        Load the list of papers for a specific conference and year.
        """

        logging.info(f"[SUMMARIZER] Loading paper list for {conference} {year}")
        raw_list_path = os.path.join("papers", "raw_list", f"{conference.lower()}_{year}.jsonl")

        if not os.path.exists(raw_list_path):
            msg = f"Raw paper list not found: {raw_list_path}. First fetch the raw paper list using PaperCrawler!"
            logging.error(msg)
            raise FileNotFoundError(msg)

        papers = []
        with open(raw_list_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    papers.append(json.loads(line))
                except json.JSONDecodeError:
                    logging.warning(f"[SUMMARIZER] Failed to parse line in {raw_list_path}: {line}")
                    continue

        return papers


    def filter_paper_by_topic(self, topic: str, keyword_list: str = os.path.join("configs", "keywords.json")):
        """
        Filter papers by a specific research topic.

        Args:
            topic (str): The research topic to filter papers by.
            keyword_list (str): Path to the JSON file containing keywords for each topic.
        """
        with open(keyword_list, "r", encoding="utf-8") as f:
            all_keywords = json.load(f)
        
        topic = (topic or "").strip().lower()
        if topic not in all_keywords:
            raise ValueError(f"Topic {topic!r} not found in keywords.json. Available topics: {list(all_keywords.keys())}")
        
        keywords = all_keywords[topic]
        if not keywords:
            raise ValueError(f"No keywords found for topic {topic!r} in keywords.json.")
        
        filtered_papers = []
        with open(self.raw_list, "r", encoding="utf-8") as f:
            for line in f:
                paper = json.loads(line)
                title = (paper.get("title") or "").lower()
                abstract = (paper.get("abstract") or "").lower()
                if any(kw.lower() in title or kw.lower() in abstract for kw in keywords):
                    filtered_papers.append(paper)
        
        return filtered_papers
    
    def summarize_single_paper(self, paper_info: dict):
        """
        Summarize a single paper into a structured format.
        """
        # Placeholder for actual summarization logic using an LLM or other methods.
        summary = {
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "abstract": paper.get("abstract", ""),
            "summary": "This is a placeholder summary."
        }
        return summary
        