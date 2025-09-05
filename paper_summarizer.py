from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import json
import logging
import argparse
from tqdm import tqdm
from configs.log_config import configure_logging
from utils.prompts import PAPER_SUMMARY_PROMPT_CH, PAPER_SUMMARY_PROMPT_EN
from utils.call_llms import get_llm
from utils.paper_crawler import download_pdf, delete_pdf, parse_pdf
from utils.helper_func import make_response, save_md_file, safe_filename


class PaperSummarizer:
    def __init__(
        self,
        model_name: str,
        api: str = "mlops",
        paper_list_root: os.PathLike | str = os.path.join("papers", "paper_list"),
        paper_summary_root: os.PathLike | str = os.path.join("papers", "paper_summary"),
        temp_pdf_root: os.PathLike | str = os.path.join("temp", "pdfs"),
    ):
        self.llm = get_llm(api, model_name)
        self.paper_list_root = Path(paper_list_root)
        self.paper_summary_root = Path(paper_summary_root)
        self.temp_pdf_root = Path(temp_pdf_root)
        self.LANG_PROMPTS = {
                "EN": PAPER_SUMMARY_PROMPT_EN,
                "CH": PAPER_SUMMARY_PROMPT_CH,
            }

        # Expect: paper_list_root must exist and be a directory
        if not self.paper_list_root.is_dir():
            msg = f"[SUMMARIZER] Paper list directory does not exist: {self.paper_list_root}"
            logging.error(msg)
            raise ValueError(msg)

        # Ensure output/temp dirs exist
        self.paper_summary_root.mkdir(parents=True, exist_ok=True)
        self.temp_pdf_root.mkdir(parents=True, exist_ok=True)

    def load_paper_list(self, raw_list_path: str) -> List[Dict[str, Any]]:
        """Load a JSONL list of papers (one JSON object per line)."""
        path = Path(raw_list_path)
        if not path.is_file():
            msg = f"[SUMMARIZER] Paper list file does not exist: {path}"
            logging.error(msg)
            raise FileNotFoundError(msg)

        papers: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        papers.append(obj)
                    else:
                        logging.warning(f"[SUMMARIZER] Non-dict row at line {i} in {path}; skipped.")
                except json.JSONDecodeError:
                    logging.warning(f"[SUMMARIZER] Malformed JSON at line {i} in {path}; skipped.")
        return papers

    def get_paper_content(self, paper_title: str, paper_url: str) -> Dict[str, Any]:
        """Fetch PDF, parse text, return make_response dict with 'data' = text."""
        if not paper_url:
            msg = f"[SUMMARIZER] No paper URL for '{paper_title}'."
            logging.warning(msg)
            return make_response("warning", msg, None)
        if not paper_title:
            msg = "[SUMMARIZER] Paper title is empty."
            logging.warning(msg)
            return make_response("warning", msg, None)

        safe_name = safe_filename(paper_title)
        pdf_path = self.temp_pdf_root / f"{safe_name}.pdf"

        try:
            download_pdf(paper_url, str(pdf_path))
            res = parse_pdf(str(pdf_path))  # expected: {"status": "...", "data": "...", "message": "..."}
            if res.get("status") == "success":
                return make_response("success", "Paper content extracted successfully.", res.get("data"))
            else:
                msg = "Failed to extract paper content: " + (res.get("message") or "Unknown error")
                logging.error(f"[SUMMARIZER] {msg}")
                return make_response("error", msg, None)
        except Exception as e:
            msg = f"[SUMMARIZER] Exception during PDF processing: {e}"
            logging.exception(msg)
            return make_response("error", msg, None)
        finally:
            # Best-effort cleanup
            try:
                delete_pdf(str(pdf_path))
            except Exception:
                pass

    def make_summary(self, paper_title: str, authors: str, paper_content: str, prompt: str) -> Dict[str, Any]:
        """Call LLM to summarize content; return make_response dict with 'data' = summary text."""
        if not paper_content:
            msg = f"[SUMMARIZER] No paper content for '{paper_title}'."
            logging.warning(msg)
            return make_response("warning", msg, None)
        if not prompt:
            msg = f"[SUMMARIZER] No prompt provided for '{paper_title}'."
            logging.warning(msg)
            return make_response("warning", msg, None)

        try:
            rsp = self.llm(prompt.format(text=paper_content, title=paper_title, authors=authors))
            if not isinstance(rsp, dict) or rsp.get("status") != "success":
                msg = f"[SUMMARIZER] LLM call failed: {rsp.get('message', 'unknown error') if isinstance(rsp, dict) else rsp}"
                logging.error(msg)
                return make_response("error", msg, None)

            response_text = rsp.get("data", "")
            if not isinstance(response_text, str) or not response_text.strip():
                msg = f"[SUMMARIZER] Empty or non-string LLM response: {response_text!r}"
                logging.error(msg)
                return make_response("error", msg, None)

            return make_response("success", "Paper summarized successfully.", response_text)
        except Exception as e:
            msg = f"[SUMMARIZER] Exception during LLM call: {e}"
            logging.exception(msg)
            return make_response("error", msg, None)

    def summarize_papers(
        self,
        conference: str,
        year: int,
        topic: Optional[str] = None,
        customize_list: bool = False,
    ) -> None:
        """
        Summarize papers for a given conference/year/topic.
        - Uses EN/CH prompts.
        - Skips summaries that already exist on disk.
        - Saves summaries as Markdown files in paper_summary_root.
        """

        # Decide which paper list to load and where summaries should go
        if customize_list:
            # Custom list goes in its own folder
            raw_list_path = self.paper_list_root / "customized" / "full_list.jsonl"
            summary_base  = self.paper_summary_root / "customized"
        else:
            # Normalize conference name (lowercase, strip spaces)
            conf_key = (conference or "").strip().lower()
            if topic:
                # Normalize topic string for safe filename
                topic_key = "".join(
                    c if c.isalnum() or c in ("-", "_") else "_"
                    for c in (topic or "").strip().lower()
                ).strip("_") or "topic"
                # If topic is provided, filter list is used
                raw_list_path = self.paper_list_root / f"{conf_key}_{year}" / f"filtered_{topic_key}.jsonl"
            else:
                # Otherwise use the full list of that conference/year
                raw_list_path = self.paper_list_root / f"{conf_key}_{year}" / "full_list.jsonl"
            # Summaries for this conf/year go here
            summary_base = self.paper_summary_root / f"{conf_key}_{year}"

        # --- Load paper list ------------------------------------------------------

        if not raw_list_path.exists():
            raise FileNotFoundError(f"[SUMMARIZER] Paper list not found: {raw_list_path}")

        papers = self.load_paper_list(str(raw_list_path))
        if not papers:
            raise ValueError(f"[SUMMARIZER] No papers in: {raw_list_path}")

        # --- Process each paper ---------------------------------------------------
        for paper in tqdm(papers, desc="Summarizing papers"):
            title = str(paper.get("title", "untitled")).strip()
            authors = str(paper.get("authors", "[]")).strip()
            url   = str(paper.get("paper_url", "")).strip()
            fname = safe_filename(title)  # sanitize title for use as filename

            # Build mapping: suffix ("EN"/"CH") → file path where summary should go
            targets = {suf: (summary_base / suf / f"{fname}.md") for suf in self.LANG_PROMPTS}

            # Ensure summary directories exist
            for p in targets.values():
                p.parent.mkdir(parents=True, exist_ok=True)

            # Figure out which languages are missing summaries (don’t overwrite existing files)
            missing = [suf for suf, p in targets.items() if not p.exists()]
            if not missing:
                continue  # Skip this paper entirely (already has EN + CH summaries)

            # Download & parse PDF only if at least one summary is missing
            content_rsp = self.get_paper_content(title, url)
            if content_rsp.get("status") != "success":
                logging.warning(
                    f"[SUMMARIZER] Content failed for '{title}': {content_rsp.get('message')}"
                )
                continue

            text = content_rsp.get("data") or ""

            # --- Generate summaries for missing languages -------------------------
            for suf in missing:
                summary_rsp = self.make_summary(title, authors, text, self.LANG_PROMPTS[suf])
                if summary_rsp.get("status") != "success":
                    logging.warning(
                        f"[SUMMARIZER] Summary failed for '{title}' ({suf}): "
                        f"{summary_rsp.get('message')}"
                    )
                    continue

                summary = summary_rsp.get("data", "")
                if not summary:
                    logging.warning(f"[SUMMARIZER] Empty summary for '{title}' ({suf})")
                    continue

                # Save summary as Markdown
                save_md_file(summary, str(targets[suf]))
                logging.info(f"[SUMMARIZER] Saved {suf} summary for '{title}' → {targets[suf]}")

if __name__ == "__main__":
    configure_logging()

    parser = argparse.ArgumentParser(description="Keyword Generator for Research Topics")
    parser.add_argument("--model_name", type=str, required=True, help="The LLM to use (e.g., 'gemini-2.5-flash', 'llama3.3-70b')")
    parser.add_argument("--api", type=str, default="mlops", help="The API to use ('mlops' or 'gemini')")
    parser.add_argument("--conference", type=str, default=None, help="The conference to focus on")
    parser.add_argument("--year", type=int, default=None, help="The year to focus on")
    parser.add_argument("--topic", type=str, default=None, help="The research topic to focus on")
    args = parser.parse_args()

    # Initialize the paper summarizer
    summarizer = PaperSummarizer(
        model_name=args.model_name,
        api=args.api
    )

    summarizer.summarize_papers(
        conference=args.conference,
        year=args.year,
        topic=args.topic
    )