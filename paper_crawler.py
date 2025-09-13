from typing import List, Dict, Any, Callable
from pathlib import Path
import os
import logging
from configs.log_config import configure_logging
from utils.paper_process import fetch_papers
from utils.helper_func import load_jsonl, save_jsonl, update_jsonl
import argparse


class PaperCrawler:
    def __init__(self, paper_list_root: os.PathLike | str = os.path.join("papers", "paper_list")):
        self.paper_list_root = Path(paper_list_root)
        self.paper_list_root.mkdir(parents=True, exist_ok=True)

    def crawl_papers(self, conference: str, year: int) -> List[Dict[str, Any]]:
        """Crawl papers for a conference/year and save as JSONL; return the list."""

        logging.info(f"[CRAWL] Fetching papers from {conference} {year}.")
        conf_key = (conference or "").strip().lower()
        crawl_res = fetch_papers(conf_key, int(year))
        if crawl_res['status'] != 'success':
            msg = f"[CRAWL] Failed to fetch papers for {conference} {year}: {crawl_res.get('message')}"
            logging.exception(msg)
            raise RuntimeError(msg)
        else:
            paper_list = crawl_res.get('data')

        # Use Path composition for clarity
        save_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
        self.save_result(paper_list, save_path)
        logging.info(f"[CRAWL] Paper list saved into {save_path}.")
        return paper_list

    @staticmethod
    def _norm_title(paper: Dict[str, Any]) -> str:
        t = paper.get("title")
        return t.strip().lower() if isinstance(t, str) else ""

    def save_result(self, paper_list: List[Dict[str, Any]], save_path: Path) -> int:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        added = update_jsonl(path, [p for p in paper_list if isinstance(p, dict)])
        logging.info(f"[CRAWL] Added {added} new papers to {path}")
        return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper Crawler")
    parser.add_argument("--conf", type=str, required=True, help="Conference to analyze")
    parser.add_argument("--year", type=int, default=2025, help="Year of the conference")
    args = parser.parse_args()

    configure_logging(console=True, console_level=logging.INFO, colored_console=True)
    crawler = PaperCrawler()
    crawler.crawl_papers(args.conf, args.year)