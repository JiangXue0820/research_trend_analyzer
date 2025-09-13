from typing import Any, Dict, List, Union, Optional, Tuple
from pathlib import Path
import os
import json
import logging
from utils.helper_func import load_jsonl
from utils.call_llms import get_llm
from utils.prompts import PAPER_FILTER_PROMPT
from configs.log_config import configure_logging
from tqdm import tqdm
import argparse

class PaperFilter:
    def __init__(
        self,
        scope_list_path: Union[os.PathLike, str] = os.path.join("configs", "analysis_scope.json"),
        paper_list_root: Union[os.PathLike, str] = os.path.join("papers", "paper_list"),
        model_name: Optional[str] = "gemini-2.5-flash",
        api: Optional[str] = "mlops",
    ):
        self.scope_list_path = Path(scope_list_path)
        self.paper_list_root = Path(paper_list_root)
        self.model_name = model_name
        self.api = api
        self.llm = get_llm(api, model_name) if model_name else None

        # runtime store
        self._filtered_path: Optional[Path] = None
        self._filtered_index: set[str] = set()          # 去重索引（仅 url/title）
        self._existing_papers: List[Dict[str, Any]] = []  # 已有条目缓存（仅在 run 初始化时加载一次）

        if not self.scope_list_path.is_file():
            msg = f"[PAPER_FILTER] Scope list file does not exist: {self.scope_list_path}"
            logging.warning(msg); raise ValueError(msg)
        if not self.paper_list_root.is_dir():
            msg = f"[PAPER_FILTER] Paper list directory does not exist: {self.paper_list_root}"
            logging.warning(msg); raise ValueError(msg)

    # ---------- helpers for per-topic store & dedupe ----------

    @staticmethod
    def _sanitize_topic(topic: str) -> str:
        return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (topic or "").strip().lower()).strip("_") or "topic"

    @staticmethod
    def _paper_key(paper: Dict[str, Any]) -> str:
        """Dedup key based ONLY on url or title (lowercased). Prefer url; fallback to title."""
        url = str(paper.get("url", "")).strip().lower()
        if url:
            return f"url::{url}"
        title = str(paper.get("title", "")).strip().lower()
        return f"title::{title}"

    def _topic_file_path(self, conference: str, year: int, topic: str) -> Path:
        conf_key = (conference or "").strip().lower()
        topic_key = self._sanitize_topic(topic)
        return self.paper_list_root / f"{conf_key}_{year}" / f"filtered_{topic_key}.jsonl"

    def _init_filtered_store(self, conference: str, year: int, topic: str) -> Tuple[int, Path]:
        """
        若文件存在→加载为 existing_papers 并建索引；若不存在→创建空文件，existing_papers=[]。
        """
        filtered_path = self._topic_file_path(conference, year, topic)
        filtered_path.parent.mkdir(parents=True, exist_ok=True)

        self._filtered_path = filtered_path
        self._filtered_index.clear()
        self._existing_papers = []

        if filtered_path.is_file():
            try:
                self._existing_papers = load_jsonl(str(filtered_path))
                for p in self._existing_papers:
                    try:
                        self._filtered_index.add(self._paper_key(p))
                    except Exception:
                        continue
                logging.info(f"[PAPER_FILTER] Loaded {len(self._filtered_index)} existing papers from {filtered_path}")
            except Exception as e:
                logging.warning(f"[PAPER_FILTER] Failed to load existing list, recreating. Reason: {e}")
                self._existing_papers = []
                filtered_path.touch()
        else:
            filtered_path.touch()

        return (len(self._filtered_index), filtered_path)

    def save_paper(self, paper: Dict[str, Any]) -> bool:
        """
        命中即单条写入；基于 url→title 去重。假设 _init_filtered_store 已设置 _filtered_path。
        """
        if not isinstance(paper, dict):
            return False
        if self._filtered_path is None:
            logging.error("[PAPER_FILTER] save_paper called before initializing store.")
            return False

        key = self._paper_key(paper)
        if key in self._filtered_index:
            return False

        with self._filtered_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")
        self._filtered_index.add(key)
        self._existing_papers.append(paper)
        return True

    # ---------- loading scope / source lists ----------

    def load_full_paper_list(self, conference: str, year: int) -> List[Dict[str, Any]]:
        conf_key = (conference or "").strip().lower()
        if not conf_key:
            raise ValueError("[PAPER_FILTER] Conference must be specified.")
        if not year:
            raise ValueError("[PAPER_FILTER] Year must be specified.")

        full_list_path = os.path.join(self.paper_list_root, f"{conf_key}_{year}", "full_list.jsonl")
        if not os.path.isfile(full_list_path):
            msg = f"[PAPER_FILTER] Full paper list file does not exist: {full_list_path}. Use paper_crawler.py first."
            logging.warning(msg); raise FileNotFoundError(msg)

        try:
            return load_jsonl(full_list_path)
        except Exception as e:
            msg = f"[PAPER_FILTER] Error loading full paper list from '{full_list_path}': {e}"
            logging.error(msg); raise RuntimeError(msg) from e

    def load_keywords_of_topic(self, topic: str) -> Tuple[str, List[str]]:
        topic_in = (topic or "").strip()
        if not topic_in:
            raise ValueError("[PAPER_FILTER] Topic must be non-empty.")

        try:
            with self.scope_list_path.open("r", encoding="utf-8") as f:
                scope = json.load(f)
        except Exception as e:
            msg = f"[PAPER_FILTER] Error loading scope list file '{self.scope_list_path}': {e}"
            logging.error(msg); raise RuntimeError(msg) from e

        topic_key = topic_in if topic_in in scope else (topic_in.lower() if topic_in.lower() in scope else None)
        if not topic_key:
            msg = f"[PAPER_FILTER] No keywords found for topic '{topic_in}'. Add it in analysis_scope.json."
            logging.warning(msg); raise ValueError(msg)

        definition = scope.get(topic_key, {}).get("definition", "")
        if not isinstance(definition, str) or not definition.strip():
            msg = f"[PAPER_FILTER] No valid definition for topic '{topic_key}'."
            logging.warning(msg); raise ValueError(msg)

        kws = scope.get(topic_key, {}).get("keywords")
        if not isinstance(kws, list) or not kws:
            msg = f"[PAPER_FILTER] No keywords for topic '{topic_key}'."
            logging.warning(msg); raise ValueError(msg)

        normed_kws, seen = [], set()
        for k in kws:
            if isinstance(k, str):
                s = k.strip().lower()
                if s and s not in seen:
                    seen.add(s); normed_kws.append(s)
        return definition, normed_kws

    # ---------- keyword filtering (incremental save) ----------

    def filter_papers_by_keywords(
        self,
        topic: str,
        paper_list: List[Dict[str, Any]],
    ) -> int:
        """命中即保存（单条写入）；返回新增数量。"""
        _, keywords = self.load_keywords_of_topic(topic)
        kw_set = {kw.strip().lower() for kw in keywords if isinstance(kw, str) and kw.strip()}
        if not kw_set:
            logging.warning("[PAPER_FILTER] No valid keywords provided."); return 0

        added = 0
        for paper in tqdm(paper_list, desc=f"[keyword] {topic}"):
            title = str(paper.get("title", "")).lower()
            if not title:
                continue
            if any(kw in title for kw in kw_set):
                if self.save_paper(paper):
                    added += 1
        return added

    # ---------- LLM filtering (incremental save) ----------

    @staticmethod
    def parse_llm_decision(response_text: str) -> Optional[bool]:
        """接受 '1'/'0' 或包含 decision 的 JSON/文本，返回 True/False/None。"""
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

    def filter_paper_by_llm(
        self,
        topic: str,
        paper_list: List[Dict[str, Any]]
    ) -> int:
        if self.llm is None:
            msg = "[PAPER_FILTER] LLM not configured for filter_paper_by_llm()."
            logging.error(msg); raise ValueError(msg)

        definition, keywords = self.load_keywords_of_topic(topic)
        prompt_template = PAPER_FILTER_PROMPT.format(
            topic=topic,
            definition=definition,
            keywords=", ".join(keywords),
            title="{title}"
        )

        added, fail = 0, 0
        for paper in tqdm(paper_list, desc=f"[llm] {topic}"):
            title = str(paper.get("title", "")).strip()
            if not title:
                logging.warning("[PAPER_FILTER] Empty title; skip.")
                fail += 1; continue

            paper_prompt = prompt_template.format(title=title)
            resp = self.llm(paper_prompt)
            if resp.get("status") != "success":
                logging.error(f"[PAPER_FILTER] LLM call failed for '{title}': {resp.get('message', 'unknown error')}")
                fail += 1; continue

            text = resp.get("data", "")
            if not isinstance(text, str) or not text.strip():
                logging.error(f"[PAPER_FILTER] LLM response empty for '{title}': {text!r}")
                fail += 1; continue

            decision = self.parse_llm_decision(text)
            if decision is None:
                logging.error(f"[PAPER_FILTER] Unparsable LLM response for '{title}': {text!r}")
                fail += 1; continue

            if decision and self.save_paper(paper):
                added += 1

        if fail > 0:
            logging.warning(f"[PAPER_FILTER] LLM filtering encountered {fail} failures.")
        return added

    # ---------- orchestrator ----------

    def filter_paper(self, conference: str, year: int, topic: str, method: str = "keyword") -> int:
        """
        初始化/加载（一次），逐篇筛选并即时保存；返回本轮新增数。
        """
        if not conference:
            logging.error("[PAPER_FILTER] No conference specified."); raise ValueError("Conference must be specified.")
        if not year:
            logging.error("[PAPER_FILTER] No year specified."); raise ValueError("Year must be specified.")
        if not topic:
            logging.error("[PAPER_FILTER] No topic specified."); raise ValueError("Topic must be specified.")
        if not method or method.lower() not in ["keyword", "llm"]:
            logging.error("[PAPER_FILTER] Invalid method. Use 'keyword' or 'llm'."); raise ValueError("Method must be 'keyword' or 'llm'.")

        logging.info(f"[PAPER_FILTER] Filtering papers for {conference}, {year}, {topic} (method={method})")

        # 1) init/load existing filtered store (load once, cache)
        _, filtered_path = self._init_filtered_store(conference, year, topic)

        # 2) load source list
        full_paper_list = self.load_full_paper_list(conference, year)

        # 3) filter & save incrementally
        if method.lower() == "llm":
            added_now = self.filter_paper_by_llm(conference, year, topic, full_paper_list)
        else:
            added_now = self.filter_papers_by_keywords(conference, year, topic, full_paper_list)

        after_count = len(self._filtered_index)
        logging.info(f"[PAPER_FILTER] Added {added_now} new papers; total now {after_count} in {filtered_path}")
        return added_now


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper Summarizer for Research Topics")
    parser.add_argument("--conf", type=str, required=True, help="The conference to focus on")
    parser.add_argument("--year", type=int, required=True, help="The year to focus on")
    parser.add_argument("--topic", type=str, required=True, help="The research topic to focus on")
    parser.add_argument("--model_name", type=str, default="gemini-2.5-flash", help="LLM to use")
    parser.add_argument("--api", type=str, default="gemini", help="API to use ('mlops' or 'gemini')")
    parser.add_argument("--method", type=str, default="llm", choices=['keyword', 'llm'], help="Filtering method")
    args = parser.parse_args()

    configure_logging(console=True, console_level=logging.INFO, colored_console=True)
    pf = PaperFilter(model_name=args.model_name, api=args.api)
    pf.filter_paper(args.conf, args.year, args.topic, method=args.method)
