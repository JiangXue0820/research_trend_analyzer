from typing import Any, Dict, List, Optional
import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import logging

from configs.log_config import configure_logging
from utils.helper_func import make_response, load_md_file, parse_markdown_summary, load_jsonl, safe_filename


class SummaryAggregator:
    def __init__(self, 
                 paper_list_root: os.PathLike | str = os.path.join("papers", "paper_list"),
                 paper_summary_root: os.PathLike | str = os.path.join("papers", "paper_summary")):
        
        self.paper_list_root = Path(paper_list_root)
        self.paper_summary_root = Path(paper_summary_root)

        if not self.paper_list_root.is_dir():
            msg = f"[SUMMARIZER] Paper list directory does not exist: {self.paper_list_root}"
            logging.error(msg)
            raise ValueError(msg)
        
        if not self.paper_summary_root.is_dir():
            msg = f"[SUMMARIZER] Paper summary directory does not exist: {self.paper_summary_root}"
            logging.error(msg)
            raise ValueError(msg)

    def load_paper_list(self, conference: str, year: int, topic: Optional[str] = None) -> List[Dict[str, Any]]:

        if not topic:
            self.paper_list_path = os.path.join(self.paper_list_root, f"{conference}_{year}", "full_list.jsonl")
        else:
            self.paper_list_path = os.path.join(self.paper_list_root, f"{conference}_{year}", f"filtered_{topic}.jsonl")

        if not os.path.isfile(self.paper_list_path):
            msg = f"Paper list file does not exist: {self.paper_list_path}"
            logging.error(msg)
            raise FileNotFoundError(msg)

        return load_jsonl(self.paper_list_path)

    def parse_single_summary(self, paper_title: str, authors: str, summary: str) -> Dict[str, Any]:
        """Parse a single markdown summary content into structured data."""
        res = parse_markdown_summary(summary)

        if res.get("status") != "success":
            msg = "[RESULT_VISUALIZER] Failed to parse summary."
            logging.error(f"{msg}: {res.get('message')}")
            return make_response("error", msg, None)

        parsed_content = res.get("data", {})
        if not parsed_content:
            msg = "[RESULT_VISUALIZER] No valid data found."
            logging.error(msg)
            return make_response("error", msg, None)

        
        affiliations = parsed_content.get("Paper Info", {}).get("Affiliations", [])
        keywords = parsed_content.get("Brief Summary", {}).get("Keywords", [])
        highlights = parsed_content.get("Brief Summary", {}).get("Highlight", "")

        msg = "[RESULT_VISUALIZER] Successfully parsed summary."
        logging.info(msg)
        return make_response("success", msg, {
            "Title": paper_title,
            "Authors": authors,
            "Affiliations": affiliations,
            "Keywords": keywords,
            "Highlights": highlights
        })

    def aggregate_brief_summary(self, conference: str, year: int, topic: Optional[str] = None, language: str = "CH"):

        conf_key = (conference or "").strip().lower()
        year = int(year)
        topic = (topic or "").strip().lower() if topic else None

        if not conf_key or not year:
            msg = f"[RESULT_VISUALIZER] Conference key and year must be provided. Now conference={conf_key}, year={year}"
            logging.error(msg)
            raise ValueError(msg)

        logging.info(f"[RESULT_VISUALIZER] Aggregating summary for conference={conf_key}, year={year}")
        self.papers = self.load_paper_list(conf_key, year, topic)
        self.paper_summary_path = os.path.join(self.paper_summary_root, f"{conf_key}_{year}", language)
        if not os.path.exists(self.paper_summary_path):
            msg = f"[RESULT_VISUALIZER] Paper summary directory does not exist: {self.paper_summary_path}"
            logging.error(msg)
            raise FileNotFoundError(msg)
        
        aggregated_summary = []
        failed = 0
        for paper in tqdm(self.papers, desc="Aggregating paper summaries"):
            title = str(paper.get("title", "untitled")).strip()
            authors = str(paper.get("authors", "[]")).strip()
            fname = safe_filename(title)  # sanitize title for use as filename
            print(fname)

            summary_path = os.path.join(self.paper_summary_path, f"{fname}.md")
            if not os.path.isfile(summary_path):
                logging.warning(f"[RESULT_VISUALIZER] Summary file not found for paper {title} with path {summary_path}")
                failed += 1
                continue

            load_md_res = load_md_file(os.path.join(self.paper_summary_path, f"{fname}.md"))
            if load_md_res.get("status") == "success":
                summary = load_md_res.get("data", {})
            else:
                logging.warning(f"[RESULT_VISUALIZER] Failed to load markdown file for paper: {title} with error: {load_md_res.get('message', 'Unknown error')}")
                failed += 1
                continue

            parse_res = self.parse_single_summary(title, authors, summary)
            if parse_res.get("status") == "success":
                aggregated_summary.append(parse_res.get("data"))
            else:
                logging.warning(f"[RESULT_VISUALIZER] Failed to parse summary for paper: {title} with error: {parse_res.get('message', 'Unknown error')}")
                failed += 1

        logging.info(f"[RESULT_VISUALIZER] Successfully parsed {len(aggregated_summary)} summaries, {failed} failures. Check log for more details.")

        paper_summary_excel_path = os.path.join(self.paper_summary_path, "summary.xlsx")
        summary_df = pd.DataFrame.from_records(aggregated_summary)
        summary_df.to_excel(paper_summary_excel_path, index=False)

        logging.info(f"[RESULT_VISUALIZER] Aggregated summary saved to {paper_summary_excel_path}")


if __name__ == "__main__":
    configure_logging()
    aggregator = SummaryAggregator()
    aggregator.aggregate_brief_summary(conference="neurips", year=2020, topic="privacy", language="CH")
    aggregator.aggregate_brief_summary(conference="neurips", year=2020, topic="privacy", language="EN")