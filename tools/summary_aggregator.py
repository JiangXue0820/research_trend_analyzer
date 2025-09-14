from typing import Any, Dict, List, Optional
import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import logging
from langchain.tools import BaseTool
from langchain_core.tools import tool
from pydantic import Field

from configs.log_config import configure_logging
from utils.helper_func import make_response, load_md_file, parse_markdown_summary, load_jsonl, safe_filename


@tool
def aggregate_summaries_tool(
    conference: str,
    year: int,
    topic: Optional[str] = None,
    language: str = "CH",
    paper_list_root: str = None,
    paper_summary_root: str = None
) -> Dict[str, Any]:
    """
    Aggregate and structure paper summaries into an Excel file.
    
    Args:
        conference: Conference name
        year: Conference year
        topic: Research topic (optional)
        language: Language of summaries ('CH' for Chinese, 'EN' for English)
        paper_list_root: Root directory for paper lists (optional)
        paper_summary_root: Root directory for paper summaries (optional)
        
    Returns:
        Dictionary with aggregation results
    """
    if paper_list_root is None:
        paper_list_root = os.path.join("papers", "paper_list")
    if paper_summary_root is None:
        paper_summary_root = os.path.join("papers", "paper_summary")
    
    conf_key = (conference or "").strip().lower()
    year = int(year)
    topic = (topic or "").strip().lower() if topic else None
    
    logging.info(f"[SUMMARY_AGGREGATOR] Aggregating {language} summaries for {conf_key}, {year}, {topic or 'all topics'}")
    
    try:
        # Load paper list
        if not topic:
            paper_list_path = os.path.join(paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
        else:
            paper_list_path = os.path.join(paper_list_root, f"{conf_key}_{year}", f"filtered_{topic}.jsonl")
        
        if not os.path.isfile(paper_list_path):
            return {
                "status": "error",
                "conference": conference,
                "year": year,
                "topic": topic,
                "language": language,
                "error": f"Paper list file does not exist: {paper_list_path}",
                "aggregated_count": 0
            }
        
        papers = load_jsonl(paper_list_path)
        if not papers:
            return {
                "status": "warning",
                "conference": conference,
                "year": year,
                "topic": topic,
                "language": language,
                "message": "No papers found in the list",
                "aggregated_count": 0
            }
        
        # Check if summary directory exists
        paper_summary_path = os.path.join(paper_summary_root, f"{conf_key}_{year}", language)
        if not os.path.exists(paper_summary_path):
            return {
                "status": "error",
                "conference": conference,
                "year": year,
                "topic": topic,
                "language": language,
                "error": f"Paper summary directory does not exist: {paper_summary_path}",
                "aggregated_count": 0
            }
        
        # Aggregate summaries
        aggregated_summary = []
        failed_count = 0
        
        for paper in tqdm(papers, desc=f"Aggregating {language} summaries"):
            if not isinstance(paper, dict):
                failed_count += 1
                continue
                
            title = str(paper.get("title", "untitled")).strip()
            fname = safe_filename(title)
            
            summary_path = os.path.join(paper_summary_path, f"{fname}.md")
            if not os.path.isfile(summary_path):
                logging.warning(f"[SUMMARY_AGGREGATOR] Summary file not found: {summary_path}")
                failed_count += 1
                continue
            
            # Load markdown file
            load_result = load_md_file(summary_path)
            if load_result.get("status") != "success":
                logging.warning(f"[SUMMARY_AGGREGATOR] Failed to load markdown: {load_result.get('message')}")
                failed_count += 1
                continue
            
            summary_content = load_result.get("data", "")
            
            # Parse markdown summary
            parse_result = parse_markdown_summary(summary_content)
            if parse_result.get("status") != "success":
                logging.warning(f"[SUMMARY_AGGREGATOR] Failed to parse summary: {parse_result.get('message')}")
                failed_count += 1
                continue
            
            parsed_content = parse_result.get("data", {})
            if not parsed_content:
                failed_count += 1
                continue
            
            # Extract structured data
            authors = parsed_content.get("Paper Info", {}).get("Authors", [])
            affiliations = parsed_content.get("Paper Info", {}).get("Affiliations", [])
            keywords = parsed_content.get("Brief Summary", {}).get("Keywords", [])
            highlights = parsed_content.get("Brief Summary", {}).get("Highlight", "")
            
            aggregated_summary.append({
                "Title": title,
                "Authors": authors,
                "Affiliations": affiliations,
                "Keywords": keywords,
                "Highlights": highlights
            })
        
        # Save to Excel
        if aggregated_summary:
            excel_path = os.path.join(paper_summary_path, "summary.xlsx")
            summary_df = pd.DataFrame.from_records(aggregated_summary)
            summary_df.to_excel(excel_path, index=False)
            
            logging.info(f"[SUMMARY_AGGREGATOR] Saved aggregated summary to {excel_path}")
            
            return {
                "status": "success",
                "conference": conference,
                "year": year,
                "topic": topic,
                "language": language,
                "aggregated_count": len(aggregated_summary),
                "failed_count": failed_count,
                "excel_path": excel_path,
                "message": f"Aggregated {len(aggregated_summary)} {language} summaries, {failed_count} failures"
            }
        else:
            return {
                "status": "warning",
                "conference": conference,
                "year": year,
                "topic": topic,
                "language": language,
                "message": "No summaries were successfully aggregated",
                "aggregated_count": 0,
                "failed_count": failed_count
            }
            
    except Exception as e:
        logging.exception(f"[SUMMARY_AGGREGATOR] Failed to aggregate summaries: {e}")
        return {
            "status": "error",
            "conference": conference,
            "year": year,
            "topic": topic,
            "language": language,
            "error": str(e),
            "aggregated_count": 0
        }


@tool
def parse_single_summary_tool(
    paper_title: str,
    authors: str,
    summary_content: str
) -> Dict[str, Any]:
    """
    Parse a single markdown summary into structured data.
    
    Args:
        paper_title: Paper title
        authors: Paper authors
        summary_content: Markdown summary content
        
    Returns:
        Dictionary with parsed summary data
    """
    logging.info(f"[SUMMARY_AGGREGATOR] Parsing summary for: {paper_title}")
    
    try:
        # Parse markdown summary
        parse_result = parse_markdown_summary(summary_content)
        if parse_result.get("status") != "success":
            return {
                "status": "error",
                "paper_title": paper_title,
                "error": f"Failed to parse summary: {parse_result.get('message')}",
                "parsed_data": None
            }
        
        parsed_content = parse_result.get("data", {})
        if not parsed_content:
            return {
                "status": "warning",
                "paper_title": paper_title,
                "message": "No valid data found in summary",
                "parsed_data": None
            }
        
        # Extract structured data
        affiliations = parsed_content.get("Paper Info", {}).get("Affiliations", [])
        keywords = parsed_content.get("Brief Summary", {}).get("Keywords", [])
        highlights = parsed_content.get("Brief Summary", {}).get("Highlight", "")
        
        parsed_data = {
            "Title": paper_title,
            "Authors": authors,
            "Affiliations": affiliations,
            "Keywords": keywords,
            "Highlights": highlights
        }
        
        return {
            "status": "success",
            "paper_title": paper_title,
            "parsed_data": parsed_data,
            "message": "Successfully parsed summary"
        }
        
    except Exception as e:
        logging.exception(f"[SUMMARY_AGGREGATOR] Failed to parse summary for '{paper_title}': {e}")
        return {
            "status": "error",
            "paper_title": paper_title,
            "error": str(e),
            "parsed_data": None
        }


class SummaryAggregatorTool(BaseTool):
    """Langchain tool for aggregating and structuring paper summaries"""
    
    name: str = "summary_aggregator"
    description: str = "Aggregate and structure paper summaries into Excel files for analysis"
    paper_list_root: str = Field(default=os.path.join("papers", "paper_list"), 
                               description="Root directory for paper lists")
    paper_summary_root: str = Field(default=os.path.join("papers", "paper_summary"), 
                                  description="Root directory for paper summaries")
    
    def _run(self, conference: str, year: int, topic: Optional[str] = None, language: str = "CH") -> Dict[str, Any]:
        """
        Aggregate summaries for a conference and year.
        
        Args:
            conference: Conference name
            year: Conference year
            topic: Research topic (optional)
            language: Language of summaries ('CH' or 'EN')
            
        Returns:
            Dictionary with aggregation results
        """
        return aggregate_summaries_tool(
            conference=conference,
            year=year,
            topic=topic,
            language=language,
            paper_list_root=self.paper_list_root,
            paper_summary_root=self.paper_summary_root
        )
    
    async def _arun(self, conference: str, year: int, topic: Optional[str] = None, language: str = "CH") -> Dict[str, Any]:
        """Async version of the tool"""
        return self._run(conference, year, topic, language)


# Export the tools for easy access
summary_aggregator_tools = [aggregate_summaries_tool, parse_single_summary_tool, SummaryAggregatorTool()]