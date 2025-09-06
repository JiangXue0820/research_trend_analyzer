from typing import Any, Dict, List, Union
from pathlib import Path
import os
import json
import logging
from utils.helper_func import load_jsonl, update_jsonl


class PaperFilter:
    def __init__(
        self,
        keywords_path: Union[os.PathLike, str] = os.path.join("configs", "topic_keywords.json"),
        paper_list_root: Union[os.PathLike, str] = os.path.join("papers", "paper_list"),
    ):
        self.keywords_path = Path(keywords_path)
        self.paper_list_root = Path(paper_list_root)

        if not self.keywords_path.is_file():
            msg = (
                f"[PAPER_FILTER] Keywords file does not exist: {self.keywords_path}. "
                "Cannot load keywords."
            )
            logging.warning(msg)
            raise ValueError(msg)

        if not self.paper_list_root.is_dir():
            msg = (
                f"[PAPER_FILTER] Paper list directory does not exist: {self.paper_list_root}. "
                "Cannot load papers."
            )
            logging.warning(msg)
            raise ValueError(msg)

    def load_keywords_of_topic(self, topic: str) -> List[str]:
        """
        Load and normalize keywords for a specific topic from the keywords JSON file.
        Returns lowercase, deduped keywords.
        """
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("[PAPER_FILTER] Topic must be non-empty.")

        try:
            with self.keywords_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            msg = f"[PAPER_FILTER] Error loading keywords file '{self.keywords_path}': {e}"
            logging.error(msg)
            raise RuntimeError(msg) from e

        # Try exact key, then lowercase fallback
        kws = data.get(topic)
        if kws is None:
            kws = data.get(topic.lower())

        if not isinstance(kws, list) or not kws:
            msg = (
                f"[PAPER_FILTER] No keywords found for topic '{topic}'. "
                "Generate keywords using keywords_generator.py first."
            )
            logging.warning(msg)
            raise ValueError(msg)

        # Normalize: strings only, strip+lower, dedupe
        norm = []
        seen = set()
        for k in kws:
            if isinstance(k, str):
                s = k.strip().lower()
                if s and s not in seen:
                    seen.add(s)
                    norm.append(s)
        return norm

    def load_full_paper_list(self, conference: str, year: int) -> List[Dict[str, Any]]:
        """
        Load the full paper list JSONL for the given conference/year.
        """
        conf_key = (conference or "").strip().lower()
        if not conf_key:
            raise ValueError("[PAPER_FILTER] Conference must be specified.")
        if not year:
            raise ValueError("[PAPER_FILTER] Year must be specified.")

        full_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
        if not os.path.isfile(full_list_path):
            msg = (
                f"[PAPER_FILTER] Full paper list file does not exist: {full_list_path}. "
                "Use paper_crawler.py to fetch the papers first."
            )
            logging.warning(msg)
            raise FileNotFoundError(msg)

        try:
            paper_list = load_jsonl(full_list_path)  # returns List[Dict[str, Any]]
            return paper_list
        except Exception as e:
            msg = f"[PAPER_FILTER] Error loading full paper list from '{full_list_path}': {e}"
            logging.error(msg)
            raise RuntimeError(msg) from e

    def filter_papers_by_keywords(
        self,
        paper_list: List[Dict[str, Any]],
        keywords: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Return papers whose title contains at least one keyword (case-insensitive).
        """
        kw_set = {kw.strip().lower() for kw in keywords if isinstance(kw, str) and kw.strip()}
        if not kw_set:
            logging.warning("[PAPER_FILTER] No valid keywords provided for filtering.")
            return []

        matched: List[Dict[str, Any]] = []
        for paper in paper_list:
            title = str(paper.get("title", "")).lower()
            if any(kw in title for kw in kw_set):
                matched.append(paper)
        return matched

    def save_filtered_papers(
        self,
        conference: str,
        year: int,
        topic: str,
        filtered_papers: List[Dict[str, Any]],
    ) -> None:
        """
        Save filtered papers to a JSONL file:
          papers/{conference}_{year}/filtered_{topic}.jsonl

        If the file exists: update (append only new rows, dedupe by full row content).
        If the file does not exist: create it with the given papers.
        """
        conf_key = (conference or "").strip().lower()
        topic_key = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (topic or "").strip().lower()).strip("_") or "topic"

        filtered_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", f"filtered_{topic_key}.jsonl")
        filtered_list_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # update_jsonl handles create/merge/dedupe
            added = update_jsonl(filtered_list_path, [p for p in filtered_papers if isinstance(p, dict)])
            if added > 0:
                logging.info(f"[PAPER_FILTER] Added {added} new filtered papers to {filtered_list_path}")
            else:
                logging.info(f"[PAPER_FILTER] No new filtered papers to add for {filtered_list_path}")
        except Exception as e:
            raise RuntimeError(
                f"[PAPER_FILTER] Failed to update filtered paper list at '{filtered_list_path}': {e}"
            ) from e

    def main(self, conference: str, year: int, topic: str) -> List[Dict[str, Any]]:
        """
        Filter papers by topic keywords and save the filtered list to a JSONL file.
        """
        if not conference:
            logging.error("[PAPER_FILTER] No conference specified.")
            raise ValueError("Conference must be specified.")
        if not year:
            logging.error("[PAPER_FILTER] No year specified.")
            raise ValueError("Year must be specified.")
        if not topic:
            logging.error("[PAPER_FILTER] No topic specified.")
            raise ValueError("Topic must be specified.")
        
        logging.info(f"[PAPER_FILTER] Filtering papers for {conference}, {year}, {topic}")

        keywords = self.load_keywords_of_topic(topic)
        full_paper_list = self.load_full_paper_list(conference, year)

        filtered_papers = self.filter_papers_by_keywords(full_paper_list, keywords)
        logging.info(
            f"[PAPER_FILTER] Found {len(filtered_papers)} papers matching topic '{topic}' "
            f"out of {len(full_paper_list)} total papers."
        )

        self.save_filtered_papers(conference, year, topic, filtered_papers)
        return filtered_papers


if __name__ == "__main__":
    from configs.log_config import configure_logging
    configure_logging()
    filter = PaperFilter()
    filter.main("neurips", 2020, "privacy")