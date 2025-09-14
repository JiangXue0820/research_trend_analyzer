from typing import Any, Dict, List, Union, Optional, Tuple
from pathlib import Path
import os
import json
import logging
from langchain.tools import BaseTool
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from pydantic import Field
from tqdm import tqdm

from utils.call_llms import get_llm
from configs.log_config import configure_logging
from utils.helper_func import load_jsonl, save_jsonl, update_jsonl
from utils.prompts import PAPER_FILTER_PROMPT
from utils.paper_process import paper_matches_topic




def _parse_llm_decision(response_text: str) -> Optional[bool]:
    """
    Parse LLM decision from response text.
    
    Args:
        response_text: LLM response text
        
    Returns:
        True if paper is relevant, False if not, None if undecidable
    """
    if not isinstance(response_text, str):
        return None
        
    s = response_text.strip()
    if s == "1": return True
    if s == "0": return False
    
    try:
        js = json.loads(s)
        if isinstance(js, dict) and "decision" in js:
            d = js["decision"]
            if d in (0, 1): return bool(d)
            if isinstance(d, str) and d.strip() in ("0", "1"):
                return d.strip() == "1"
    except Exception:
        pass
        
    low = s.lower()
    if "decision=1" in low or '"decision": 1' in low: return True
    if "decision=0" in low or '"decision": 0' in low: return False
    
    return None


class PaperFilterTool(BaseTool):
    """Langchain tool for filtering research papers by topic relevance"""
    
    name: str = "paper_filter"
    description: str = "Filter research papers by topic relevance using keywords or LLM assessment"
    scope_list_path: str = Field(default=os.path.join("configs", "analysis_scope.json"), 
                               description="Path to analysis scope JSON file")
    paper_list_root: str = Field(default=os.path.join("papers", "paper_list"),
                               description="Root directory for paper lists")
    api: str = Field(default="gemini", description="API to use for LLM calls")
    model_name: str = Field(default="gemini-2.5-flash", description="Model name for LLM calls")
    
    def _run(self, conference: str, year: int, topic: str, method: str = "keyword") -> Dict[str, Any]:
        """
        Filter papers for a conference and topic using specified method.

        Args:
            conference: Conference name
            year: Conference year
            topic: Research topic
            method: Filtering method ('keyword' or 'llm')

        Returns:
            Dictionary with filtering results
        """
        
        # First, load the full paper list
        conf_key = (conference or "").strip().lower()
        full_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
        
        if not os.path.isfile(full_list_path):
            return {
                "status": "error",
                "error": f"Full paper list not found: {full_list_path}. Use paper_crawler first.",
                "filtered_count": 0
            }
        
        try:
            paper_list = load_jsonl(full_list_path)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to load paper list: {e}",
                "filtered_count": 0
            }
        
        # Apply filtering based on method
        if method.lower() == "llm":
            return self._filter_by_llm(conference, year, topic, paper_list, self.scope_list_path, self.paper_list_root)
        else:
            return self._filter_by_keywords(conference, year, topic, paper_list, self.scope_list_path, self.paper_list_root)
    
    def _filter_by_keywords(self, conference: str, year: int, topic: str, paper_list: List[Dict[str, Any]],
                          scope_list_path: str, paper_list_root: str) -> Dict[str, Any]:
        """Implement keyword-based filtering directly"""
        logging.info(f"[PAPER_FILTER] Filtering papers for {conference}, {year}, {topic} using keywords")
        
        try:
            # Load keywords for the topic
            scope_path = Path(scope_list_path)
            if not scope_path.is_file():
                return {
                    "status": "error",
                    "error": f"Scope list file does not exist: {scope_path}",
                    "filtered_count": 0
                }
            
            with scope_path.open("r", encoding="utf-8") as f:
                scope = json.load(f)
            
            topic_key = topic if topic in scope else (topic.lower() if topic.lower() in scope else None)
            if not topic_key:
                return {
                    "status": "error",
                    "error": f"No keywords found for topic '{topic}'. Add it in analysis_scope.json.",
                    "filtered_count": 0
                }
            
            keywords = scope.get(topic_key, {}).get("keywords", [])
            if not isinstance(keywords, list) or not keywords:
                return {
                    "status": "error",
                    "error": f"No keywords for topic '{topic_key}'.",
                    "filtered_count": 0
                }
            
            # Normalize keywords
            kw_set = {kw.strip().lower() for kw in keywords if isinstance(kw, str) and kw.strip()}
            if not kw_set:
                return {
                    "status": "warning",
                    "message": "No valid keywords provided",
                    "filtered_count": 0
                }
            
            # Filter papers
            filtered_papers = []
            for paper in tqdm(paper_list, desc=f"[keyword] {topic}"):
                if not isinstance(paper, dict):
                    continue
                    
                title = str(paper.get("title", "")).lower()
                if not title:
                    continue
                    
                if any(kw in title for kw in kw_set):
                    filtered_papers.append(paper)
            
            # Save filtered papers
            conf_key = (conference or "").strip().lower()
            topic_key_sanitized = "".join(c if c.isalnum() or c in ("-", "_") else "_"
                                        for c in (topic or "").strip().lower()).strip("_") or "topic"
            
            save_path = os.path.join(paper_list_root, f"{conf_key}_{year}", f"filtered_{topic_key_sanitized}.jsonl")
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save to JSONL
            added = update_jsonl(save_path, filtered_papers)
            
            logging.info(f"[PAPER_FILTER] Filtered {len(filtered_papers)} papers for {topic}")
            
            return {
                "status": "success",
                "filtered_count": len(filtered_papers),
                "new_papers_added": added,
                "save_path": save_path,
                "message": f"Successfully filtered {len(filtered_papers)} papers for {topic}"
            }
            
        except Exception as e:
            logging.exception(f"[PAPER_FILTER] Failed to filter papers for {conference}, {year}, {topic}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "filtered_count": 0
            }

    def _filter_by_llm(self, conference: str, year: int, topic: str, paper_list: List[Dict[str, Any]],
                      scope_list_path: str, paper_list_root: str) -> Dict[str, Any]:
        """Implement LLM-based filtering directly"""
        logging.info(f"[PAPER_FILTER] Filtering papers for {conference}, {year}, {topic} using LLM")
        
        try:
            # Get LLM function with specified configuration
            try:
                llm_func = get_llm(self.api, self.model_name)
            except Exception as e:
                logging.exception(f"[PAPER_FILTER] Failed to get LLM function for {self.api}/{self.model_name}: {e}")
                return {
                    "status": "error",
                    "error": f"Failed to get LLM function: {e}",
                    "filtered_count": 0
                }
            
            # Load topic definition and keywords
            scope_path = Path(scope_list_path)
            if not scope_path.is_file():
                return {
                    "status": "error",
                    "error": f"Scope list file does not exist: {scope_path}",
                    "filtered_count": 0
                }
            
            with scope_path.open("r", encoding="utf-8") as f:
                scope = json.load(f)
            
            topic_key = topic if topic in scope else (topic.lower() if topic.lower() in scope else None)
            if not topic_key:
                return {
                    "status": "error",
                    "error": f"No definition found for topic '{topic}'.",
                    "filtered_count": 0
                }
            
            definition = scope.get(topic_key, {}).get("definition", "")
            keywords = scope.get(topic_key, {}).get("keywords", [])
            
            if not definition or not isinstance(definition, str):
                return {
                    "status": "error",
                    "error": f"No valid definition for topic '{topic_key}'.",
                    "filtered_count": 0
                }
            
            # Prepare prompt template
            prompt_template = PAPER_FILTER_PROMPT.format(
                topic=topic,
                definition=definition,
                keywords=", ".join(keywords),
                title="{title}"
            )
            
            # Filter papers using LLM
            filtered_papers = []
            failed_count = 0
            
            for paper in tqdm(paper_list, desc=f"[llm] {topic}"):
                if not isinstance(paper, dict):
                    continue
                    
                title = str(paper.get("title", "")).strip()
                if not title:
                    failed_count += 1
                    continue
                
                try:
                    # Call LLM function for decision
                    paper_prompt = prompt_template.format(title=title)
                    resp_msg = llm_func(paper_prompt)
                    if resp_msg.get("status") != "success":
                        logging.warning(f"[PAPER_FILTER] LLM filtering failed for '{title}': {resp_msg.get('message')}")
                        failed_count += 1
                        continue
                    
                    response_text = resp_msg.get("data", "")
                    
                    # Parse LLM decision (simple heuristic)
                    decision = _parse_llm_decision(response_text)
                    
                    if decision is True:
                        filtered_papers.append(paper)
                        
                except Exception as e:
                    logging.warning(f"[PAPER_FILTER] LLM filtering failed for '{title}': {e}")
                    failed_count += 1
            
            # Save filtered papers
            conf_key = (conference or "").strip().lower()
            topic_key_sanitized = "".join(c if c.isalnum() or c in ("-", "_") else "_"
                                        for c in (topic or "").strip().lower()).strip("_") or "topic"
            
            save_path = os.path.join(paper_list_root, f"{conf_key}_{year}", f"filtered_{topic_key_sanitized}.jsonl")
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save to JSONL
            added = update_jsonl(save_path, filtered_papers)
            
            logging.info(f"[PAPER_FILTER] LLM filtered {len(filtered_papers)} papers for {topic}")
            
            return {
                "status": "success",
                "filtered_count": len(filtered_papers),
                "failed_count": failed_count,
                "new_papers_added": added,
                "save_path": save_path,
                "message": f"LLM filtered {len(filtered_papers)} papers for {topic} ({failed_count} failures)"
            }
            
        except Exception as e:
            logging.exception(f"[PAPER_FILTER] Failed to LLM filter papers for {conference}, {year}, {topic}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "filtered_count": 0
            }

    async def _arun(self, conference: str, year: int, topic: str, method: str = "keyword") -> Dict[str, Any]:
        """Async version of the tool"""
        return self._run(conference, year, topic, method)


# Export the tools for easy access
paper_filter_tools = [PaperFilterTool()]