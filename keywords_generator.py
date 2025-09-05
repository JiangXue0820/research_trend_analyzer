from typing import List, Dict, Any, Union, Callable
from pathlib import Path
import logging
import ast
import json
import os
import argparse
from utils.prompts import KEYWORDS_GENERATION_PROMPT
from configs.env_config import Config
from configs.log_config import configure_logging
from utils.call_llms import get_llm



class KeywordGenerator:
    def __init__(
        self,
        llm: str,
        api: str = "mlops",
        save_path: Union[os.PathLike, str, None] = None
    ):
        self.save_path = Path(save_path) if save_path is not None else Path("configs") / "topic_keywords.json"
        self.llm = get_llm(api, llm)
        
    def generate_keywords(self, topic: str) -> List[str]:
        topic = (topic or "").strip()
        logging.info(f"[KEYWORD_GEN] Generating keywords for topic={topic!r}")
        prompt = KEYWORDS_GENERATION_PROMPT.format(topic=topic)

        # Call the model
        resp_msg = self.llm(prompt)
        if resp_msg.get("status") != "success":
            msg = f"LLM call failed: {resp_msg.get('message', 'unknown error')}"
            logging.error(f"[KEYWORD_GEN] {msg}")
            raise RuntimeError(msg)

        # Extract text (ensure string)
        response_text = resp_msg.get("data", "")
        if not isinstance(response_text, str) or not response_text.strip():
            msg = f"LLM response is empty or not a string: {response_text!r}"
            logging.error(f"[KEYWORD_GEN] {msg}")
            raise ValueError(msg)
        
        # Parse as Python list
        response_text = response_text.strip()
        try:
            parsed = ast.literal_eval(response_text)
            logging.info("[KEYWORD_GEN] Parsed with ast.literal_eval.")
        except Exception as e_ast:
            msg = f"response_text cannot be parsed into a Python list: {response_text!r}"
            logging.exception(f"[KEYWORD_GEN] {msg}")
            raise ValueError(msg) from e_ast

        if not isinstance(parsed, list):
            raise ValueError("Model output is not a list.")

        keywords = [k.strip().lower() for k in parsed if isinstance(k, str) and k.strip()]
        if not keywords:
            logging.warning(f"[KEYWORD_GEN] Parsed output but no keywords were extracted (topic={topic!r}).")

        logging.info(f"[KEYWORD_GEN] Extracted {len(keywords)} keywords for topic={topic!r}")
        return keywords

    def save_keywords(self, topic: str, keywords: List[str]) -> None:
        """
        Merge `keywords` into JSON mapping at self.save_path: { "<topic>": [kw1, kw2, ...], ... }
        - If topic exists: union old + new (set dedupe), then sort.
        - If not: create new entry.
        """
        topic = (topic or "").strip()
        if not keywords:
            logging.info("[KEYWORD_GEN] No keywords to save; skipping.")
            return
        if not topic:
            logging.warning("[KEYWORD_GEN] Empty topic; cannot save keywords.")
            return

        # Load existing mapping (or start fresh)
        data: Dict[str, List[str]] = {}
        if self.save_path.exists():
            try:
                with self.save_path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = {str(k): (v if isinstance(v, list) else []) for k, v in loaded.items()}
                else:
                    logging.warning(f"[KEYWORD_GEN] Expected dict at root of {self.save_path}; starting fresh.")
            except Exception as e:
                logging.exception(f"[KEYWORD_GEN] Failed to read {self.save_path}: {e}")

        # Normalize topic key to a single canonical form (lowercase)
        # If you want to preserve original casing, you can drop the `.lower()` here.
        topic_key = topic.lower()

        # Merge with set (dedupe). Lowercase old values to avoid case-dup bugs.
        old_set = set(s.strip().lower() for s in data.get(topic_key, []) if isinstance(s, str))
        new_set = set(k for k in keywords if isinstance(k, str) and k.strip())
        merged = sorted(old_set | new_set)

        data[topic_key] = merged

        # Save back
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            with self.save_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"[KEYWORD_GEN] Saved {len(merged)} keywords for topic '{topic_key}' to {self.save_path}")
        except Exception as e:
            logging.exception(f"[KEYWORD_GEN] Failed to save keywords: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keyword Generator for Research Topics")
    parser.add_argument("--llm", type=str, required=True, help="The LLM to use (e.g., 'gemini-2.5-flash', 'llama3.3-70b')")
    parser.add_argument("--api", type=str, default="mlops", help="The API to use ('mlops' or 'gemini')")
    parser.add_argument("--save_path", type=str, default=None, help="Path to save the keywords JSON file")
    args = parser.parse_args()

    configure_logging()
    keyword_gen = KeywordGenerator(llm=args.llm, api=args.api, save_path=args.save_path)

    while True:
        topic = input("[Input] Please enter a research topic (or type 'quit' to exit): ").strip()
        if topic.lower() == "quit":
            print("==> [Info] Exiting keyword generator.")
            break

        if not topic:
            print("==> [Error] Please enter a non-empty topic.")
            continue

        try:
            kws = keyword_gen.generate_keywords(topic)
            keyword_gen.save_keywords(topic, kws)
            print(f"==> [Success] Extracted and saved {len(kws)} keywords for '{topic}'.\n")
            print(f"Keywords: {kws}\n")
        except Exception as e:
            logging.exception(f"[KEYWORD_GEN] Failed for topic={topic!r}: {e}")
            print(f"==> [Error] {e} generating keywords for '{topic}'. \n")
