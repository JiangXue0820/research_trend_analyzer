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
from utils.helper_func import save_jsonl, update_jsonl


class KeywordsGenerator:
    def __init__(
        self,
        model_name: str,
        api: str = "mlops",
        keywords_path: Union[os.PathLike, str] = os.path.join("configs", "topic_keywords.json")
    ):
        self.keywords_path = Path(keywords_path) 
        self.llm = get_llm(api, model_name)
        
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
        Save keywords to a JSON file in the format:
            {
            "<topic1>": ["kw1", "kw2", ...],
            "<topic2>": [...]
            }

        - Normalizes topic/keywords to lowercase and strips whitespace.
        - Merges with existing file contents if present.
        - Dedupes with set() and sorts before saving.
        """
        topic_key = (topic or "").strip().lower()
        if not topic_key:
            logging.warning("[KEYWORD_GEN] Empty topic; cannot save keywords.")
            return

        new_set = {k.strip().lower() for k in (keywords or []) if isinstance(k, str) and k.strip()}
        if not new_set:
            logging.info("[KEYWORD_GEN] No valid keywords to save; skipping.")
            return

        path: Path = Path(self.keywords_path)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
            self.keywords_path = path

        data: Dict[str, List[str]] = {}
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = {str(k).lower(): (v if isinstance(v, list) else []) for k, v in loaded.items()}
            except Exception as e:
                logging.exception(f"[KEYWORD_GEN] Failed to read {path}: {e}")

        old_set = {kw.strip().lower() for kw in data.get(topic_key, []) if isinstance(kw, str)}
        merged = sorted(old_set | new_set)
        data[topic_key] = merged

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info(f"[KEYWORD_GEN] Saved {len(merged)} keywords for topic '{topic_key}' to {path}")
        except Exception as e:
            logging.exception(f"[KEYWORD_GEN] Failed to save keywords: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keyword Generator for Research Topics")
    parser.add_argument("--topic", type=str, required=True, help="The LLM to use (e.g., 'gemini-2.5-flash', 'llama3.3-70b')")
    parser.add_argument("--model_name", type=str, default='gemini-2.5-flash', help="The LLM to use (e.g., 'gemini-2.5-flash', 'llama3.3-70b')")
    parser.add_argument("--api", type=str, default="gemini", help="The API to use ('mlops' or 'gemini')")
    parser.add_argument("--keywords_path", type=str, default=os.path.join("configs", "topic_keywords.json"), help="Path to save the keywords JSON file")
    parser.add_argument("--repeat", type=int, default=5, help="Number of repeat rounds for generating keywords. Increase the repeat rounds to generate more keywords for a given topic.")
    args = parser.parse_args()

    configure_logging(console=True, console_level=logging.DEBUG, colored_console=True)
    keyword_gen = KeywordsGenerator(model_name=args.model_name, api=args.api, keywords_path=args.keywords_path)

    try:
        keywords = []
        for _ in range(args.repeat):
            kws = keyword_gen.generate_keywords(args.topic)
            keywords.extend(kws)
            keyword_gen.save_keywords(args.topic, kws)
        print(f"==> [Success] Extracted and saved {len(keywords)} keywords for '{args.topic}'.\n")
        print(f"Keywords: {set(keywords)}\n")
    except Exception as e:
        logging.exception(f"[KEYWORD_GEN] Failed for topic={args.topic!r}: {e}")
        print(f"==> [Error] {e} generating keywords for '{args.topic}'. \n")
