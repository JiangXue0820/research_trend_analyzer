from typing import List, Dict, Any, Callable
from pathlib import Path
import os
import logging
from configs.log_config import configure_logging
from utils.paper_process import fetch_neurips_papers, fetch_aaai_papers
from utils.helper_func import load_jsonl, save_jsonl, update_jsonl


class PaperCrawler:
    def __init__(self, paper_list_root: os.PathLike | str = os.path.join("papers", "paper_list")):
        self.paper_list_root = Path(paper_list_root)
        self.paper_list_root.mkdir(parents=True, exist_ok=True)
        self.craw_func_mapping: Dict[str, Callable[[int], List[Dict[str, Any]]]] = {
            "neurips": fetch_neurips_papers,
            "aaai": fetch_aaai_papers,
        }

    def crawl_papers(self, conference: str, year: int) -> List[Dict[str, Any]]:
        """Crawl papers for a conference/year and save as JSONL; return the list."""
        conf_key = (conference or "").strip().lower()
        if conf_key not in self.craw_func_mapping:
            logging.warning(f"[CRAWL] Unsupported conference: {conference}")
            raise ValueError(f"Unsupported conference: {conference}. Try one of {list(self.craw_func_mapping.keys())}")

        logging.info(f"[CRAWL] Fetching papers from {conference} {year}.")
        crawl_func = self.craw_func_mapping[conf_key]

        try:
            paper_list = crawl_func(int(year)) or []
        except Exception as e:
            logging.exception(f"[CRAWL] Failed to fetch papers for {conference} {year}: {e}")
            raise

        logging.info(f"[CRAWL] Fetched {len(paper_list)} papers from {conference} {year}.")

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
    configure_logging()
    crawler = PaperCrawler()
    crawler.crawl_papers("neurips", 2020)
