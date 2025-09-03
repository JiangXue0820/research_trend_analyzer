from typing import List, Dict, Any, Callable
from pathlib import Path
import os
import json
import logging
from configs.log_config import configure_logging
from utils.paper_crawler import fetch_neurips_papers, fetch_aaai_papers

class PaperCrawler:
    def __init__(self, root_dir: os.PathLike | str = os.path.join("papers", "raw_list")):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
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

        save_path = self.root_dir / f"{conf_key}_{year}.jsonl"
        self.save_result(paper_list, save_path)
        logging.info(f"[CRAWL] Paper list saved into {save_path}.")
        return paper_list

    @staticmethod
    def _norm_title(paper: Dict[str, Any]) -> str:
        t = paper.get("title")
        return t.strip().lower() if isinstance(t, str) else ""

    def save_result(self, paper_list: List[Dict[str, Any]], save_path: Path) -> int:
        """
        Append unique papers to a JSONL file (one JSON object per line).
        Deduplication key: normalized 'title'. Returns the number of new papers written.
        """
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing titles
        seen: set[str] = set()
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        s = line.strip()
                        if not s:
                            continue
                        try:
                            t = self._norm_title(json.loads(s))
                            if t:
                                seen.add(t)
                        except json.JSONDecodeError:
                            logging.warning(f"[CRAWL] Skipping malformed JSON line {i} in {path}")
            except Exception as e:
                logging.exception(f"[CRAWL] Failed to read {path}: {e}")

        # Filter new papers
        new_papers: List[Dict[str, Any]] = []
        for p in paper_list:
            if not isinstance(p, dict):
                continue
            t = self._norm_title(p)
            if t and t not in seen:
                seen.add(t)
                new_papers.append(p)

        if not new_papers:
            logging.info(f"[CRAWL] No new papers for {path} (all duplicates).")
            return 0

        # Ensure prior newline if needed
        try:
            need_prefix_nl = path.exists() and path.stat().st_size > 0
        except Exception:
            need_prefix_nl = False

        # Append
        try:
            with path.open("a", encoding="utf-8") as f:
                if need_prefix_nl:
                    f.write("\n")  # in case file doesn't end with newline
                f.write("\n".join(json.dumps(p, ensure_ascii=False) for p in new_papers))
                f.write("\n")
            logging.info(f"[CRAWL] Added {len(new_papers)} new papers to {path}")
            return len(new_papers)
        except Exception as e:
            logging.exception(f"[CRAWL] Failed to append to {path}: {e}")
            return 0


if __name__ == "__main__":
    configure_logging()
    crawler = PaperCrawler()
    crawler.crawl_papers("neurips", 2021)