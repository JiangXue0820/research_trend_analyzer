from typing import Any, Dict, List, Optional, Union
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
from utils.prompts import PAPER_SUMMARY_PROMPT_CH, PAPER_SUMMARY_PROMPT_EN
from utils.paper_process import download_pdf, delete_pdf, parse_pdf
from utils.helper_func import make_response, save_md_file, safe_filename, load_jsonl


class PaperSummarizerTool(BaseTool):
    """Langchain tool for summarizing research papers"""
    
    name: str = "paper_summarizer"
    description: str = "Summarize research papers using LLM, supporting both English and Chinese summaries"
    scope_list_path: str = Field(default=os.path.join("configs", "analysis_scope.json"),
                               description="Path to analysis scope JSON file")
    paper_list_root: str = Field(default=os.path.join("papers", "paper_list"),
                               description="Root directory for paper lists")
    paper_summary_root: str = Field(default=os.path.join("papers", "paper_summary"),
                                  description="Root directory for paper summaries")
    temp_pdf_root: str = Field(default=os.path.join("temp", "pdfs"),
                             description="Temporary directory for PDF downloads")
    api: str = Field(default="gemini", description="API to use for LLM calls")
    model_name: str = Field(default="gemini-2.5-flash", description="Model name for LLM calls")
    
    def _run(self, conference: str, year: int, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Summarize papers for a conference and year.

        Args:
            conference: Conference name
            year: Conference year
            topic: Research topic (optional)

        Returns:
            Dictionary with summarization results
        """
        logging.info(f"[SUMMARIZER] Batch summarizing papers for {conference}, {year}, {topic or 'all topics'}")
        
        try:
            # Determine which paper list to load
            conf_key = (conference or "").strip().lower()
            if topic:
                # Use filtered list for specific topic
                topic_key = "".join(c if c.isalnum() or c in ("-", "_") else "_"
                                  for c in (topic or "").strip().lower()).strip("_") or "topic"
                raw_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", f"filtered_{topic_key}.jsonl")
                summary_base = os.path.join(self.paper_summary_root, f"{conf_key}_{year}", topic_key)
            else:
                # Use full list
                raw_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
                summary_base = os.path.join(self.paper_summary_root, f"{conf_key}_{year}")
            
            # Load paper list
            if not os.path.isfile(raw_list_path):
                return {
                    "status": "error",
                    "conference": conference,
                    "year": year,
                    "topic": topic,
                    "error": f"Paper list not found: {raw_list_path}",
                    "papers_processed": 0
                }
            
            papers = load_jsonl(raw_list_path)
            if not papers:
                return {
                    "status": "warning",
                    "conference": conference,
                    "year": year,
                    "topic": topic,
                    "message": "No papers found in the list",
                    "papers_processed": 0
                }
            
            # Process each paper
            results = []
            for paper in tqdm(papers, desc=f"Summarizing papers for {conference} {year}"):
                if not isinstance(paper, dict):
                    continue
                    
                result = self._summarize_paper(
                    paper,
                    topic,
                    self.scope_list_path,
                    summary_base,
                    self.temp_pdf_root,
                    self.api,
                    self.model_name
                )
                results.append(result)
            
            # Count successes and failures
            successful = sum(1 for r in results if r.get("status") == "success")
            failed = len(results) - successful
            
            return {
                "status": "success",
                "conference": conference,
                "year": year,
                "topic": topic,
                "papers_processed": len(results),
                "successful_summaries": successful,
                "failed_summaries": failed,
                "message": f"Processed {len(results)} papers, {successful} successful, {failed} failed"
            }
            
        except Exception as e:
            logging.exception(f"[SUMMARIZER] Failed to batch summarize papers for {conference}, {year}: {e}")
            return {
                "status": "error",
                "conference": conference,
                "year": year,
                "topic": topic,
                "error": str(e),
                "papers_processed": 0
            }
    
    def _summarize_paper(self, paper: Dict[str, Any], topic: Optional[str], scope_list_path: str,
                        paper_summary_root: str, temp_pdf_root: str, api: str, model_name: str) -> Dict[str, Any]:
        """Implement paper summarization directly"""
        # Get LLM function with specified configuration
        try:
            llm_func = get_llm(api, model_name)
        except Exception as e:
            logging.exception(f"[SUMMARIZER] Failed to get LLM function for {api}/{model_name}: {e}")
            return {
                "status": "error",
                "paper_title": "unknown",
                "error": f"Failed to get LLM function: {e}",
                "summaries_generated": 0
            }
        
        title = str(paper.get("title", "untitled")).strip()
        url = str(paper.get("paper_url", "")).strip()
        
        logging.info(f"[SUMMARIZER] Summarizing paper: {title} with {api}/{model_name}")
        
        try:
            # Load scope and keywords if topic is provided
            keywords = ""
            if topic:
                scope_path = Path(scope_list_path)
                if scope_path.is_file():
                    with scope_path.open("r", encoding="utf-8") as f:
                        scope = json.load(f)
                    keywords_list = scope.get(topic, [])
                    keywords = ", ".join(keywords_list) if keywords_list else ""
            
            # Download and parse PDF
            safe_name = safe_filename(title)
            pdf_path = os.path.join(temp_pdf_root, f"{safe_name}.pdf")
            Path(temp_pdf_root).mkdir(parents=True, exist_ok=True)
            
            # Download PDF
            download_result = download_pdf(url, pdf_path)
            if download_result.get("status") != "success":
                return {
                    "status": "error",
                    "paper_title": title,
                    "error": f"Failed to download PDF: {download_result.get('message')}",
                    "summaries_generated": 0
                }
            
            # Parse PDF
            parse_result = parse_pdf(pdf_path)
            if parse_result.get("status") != "success":
                return {
                    "status": "error",
                    "paper_title": title,
                    "error": f"Failed to parse PDF: {parse_result.get('message')}",
                    "summaries_generated": 0
                }
            
            paper_content = parse_result.get("data", "")
            
            # Language prompts
            lang_prompts = {
                "EN": PAPER_SUMMARY_PROMPT_EN,
                "CH": PAPER_SUMMARY_PROMPT_CH
            }
            
            summaries = {}
            summary_paths = {}
            
            # Create summary directory structure
            summary_base = Path(paper_summary_root) / "general"
            for lang in lang_prompts.keys():
                lang_dir = summary_base / lang
                lang_dir.mkdir(parents=True, exist_ok=True)
                summary_paths[lang] = lang_dir / f"{safe_name}.md"
            
            # Generate summaries for each language
            for lang, prompt_template in lang_prompts.items():
                if summary_paths[lang].exists():
                    logging.info(f"[SUMMARIZER] {lang} summary already exists for '{title}', skipping")
                    continue
                
                try:
                    # Format prompt
                    prompt = prompt_template.format(
                        text=paper_content,
                        title=title,
                        keywords=keywords
                    )
                    
                    # Call LLM function
                    resp_msg = llm_func(prompt)
                    if resp_msg.get("status") != "success":
                        logging.warning(f"[SUMMARIZER] Failed to generate {lang} summary for '{title}': {resp_msg.get('message')}")
                        continue
                    
                    summary_text = resp_msg.get("data", "")
                    
                    if not summary_text or not summary_text.strip():
                        logging.warning(f"[SUMMARIZER] Empty {lang} summary for '{title}'")
                        continue
                    
                    # Save summary
                    save_md_file(summary_text, str(summary_paths[lang]))
                    summaries[lang] = summary_text
                    logging.info(f"[SUMMARIZER] Saved {lang} summary for '{title}'")
                    
                except Exception as e:
                    logging.exception(f"[SUMMARIZER] Failed to generate {lang} summary for '{title}': {e}")
            
            # Clean up temporary PDF
            try:
                delete_pdf(pdf_path)
            except Exception:
                pass
            
            return {
                "status": "success",
                "paper_title": title,
                "summaries_generated": len(summaries),
                "languages": list(summaries.keys()),
                "summary_paths": {lang: str(path) for lang, path in summary_paths.items()},
                "message": f"Successfully generated {len(summaries)} summaries for '{title}'"
            }
            
        except Exception as e:
            logging.exception(f"[SUMMARIZER] Failed to summarize paper '{title}': {e}")
            return {
                "status": "error",
                "paper_title": title,
                "error": str(e),
                "summaries_generated": 0
            }

    async def _arun(self, conference: str, year: int, topic: Optional[str] = None) -> Dict[str, Any]:
        """Async version of the tool"""
        return self._run(conference, year, topic)


# Export the tools for easy access
paper_summarizer_tools = [PaperSummarizerTool()]