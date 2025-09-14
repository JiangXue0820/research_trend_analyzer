from typing import List, Dict, Any, Union
from pathlib import Path
import os
import logging
from langchain.tools import BaseTool
from langchain_core.tools import tool
from pydantic import Field

from configs.log_config import configure_logging
from utils.paper_process import fetch_papers
from utils.helper_func import load_jsonl, save_jsonl, update_jsonl


class PaperCrawlerTool(BaseTool):
    """Langchain tool for crawling research papers from academic conferences"""
    
    name: str = "paper_crawler"
    description: str = "Crawl research papers from academic conferences and save them to JSONL files"
    paper_list_root: str = Field(default=os.path.join("papers", "paper_list"), 
                               description="Root directory to save paper lists")
    
    def _run(self, conference: str, year: int) -> Dict[str, Any]:
        """
        Crawl papers from a conference and year, automatically saving them.

        Args:
            conference: The conference name (e.g., 'neurips', 'popets', 'usenix_security')
            year: The conference year

        Returns:
            Dictionary with crawl results
        """
        
        logging.info(f"[CRAWL] Fetching papers from {conference} {year}.")
        conf_key = (conference or "").strip().lower()
        
        try:
            # Fetch papers using the paper_process module
            crawl_res = fetch_papers(conf_key, int(year))
            
            if crawl_res['status'] != 'success':
                msg = f"[CRAWL] Failed to fetch papers for {conference} {year}: {crawl_res.get('message')}"
                logging.error(msg)
                return {
                    "status": "error",
                    "conference": conference,
                    "year": year,
                    "error": msg,
                    "papers_count": 0
                }
            
            paper_list = crawl_res.get('data', [])
            
            # Save the results
            save_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save papers to JSONL file
            added = update_jsonl(save_path, [p for p in paper_list if isinstance(p, dict)])
            
            logging.info(f"[CRAWL] Added {added} new papers to {save_path}")
            
            return {
                "status": "success",
                "conference": conference,
                "year": year,
                "papers_count": len(paper_list),
                "new_papers_added": added,
                "save_path": save_path,
                "message": f"Successfully crawled {len(paper_list)} papers from {conference} {year}"
            }
            
        except Exception as e:
            logging.exception(f"[CRAWL] Failed to crawl papers for {conference} {year}: {e}")
            return {
                "status": "error",
                "conference": conference,
                "year": year,
                "error": str(e),
                "papers_count": 0
            }
    
    async def _arun(self, conference: str, year: int) -> Dict[str, Any]:
        """Async version of the tool"""
        return self._run(conference, year)


# Export the tools for easy access
paper_crawler_tools = [PaperCrawlerTool()]


# Supported conferences for documentation
SUPPORTED_CONFERENCES = {
    "neurips": "Neural Information Processing Systems",
    "popets": "Proceedings on Privacy Enhancing Technologies",
    "usenix_security": "USENIX Security Symposium", 
    "usenix_soup": "USENIX Symposium on Usable Privacy and Security",
    "acl_long": "ACL Anthology Long Papers",
    "acl_findings": "ACL Anthology Findings Papers"
}