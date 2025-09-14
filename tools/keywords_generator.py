from typing import List, Dict, Any, Union
from pathlib import Path
import logging
import ast
import json
import os
from langchain.tools import BaseTool
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from pydantic import Field

from utils.call_llms import get_llm
from configs.log_config import configure_logging
from utils.helper_func import save_jsonl, update_jsonl
from utils.prompts import KEYWORDS_GENERATION_PROMPT


@tool
def generate_keywords_tool(topic: str, model_name: str = "gemini-2.5-flash", api: str = "gemini") -> List[str]:
    """
    Generate research keywords for a given topic using LLM.
    
    Args:
        topic: The research topic to generate keywords for
        model_name: LLM model name (default: gpt-4-turbo)
        api: LLM API provider: 'openai' or 'google' (default: openai)
        
    Returns:
        List of generated keywords
    """
    topic = (topic or "").strip()
    logging.info(f"[KEYWORD_GEN] Generating keywords for topic={topic!r} with {api}/{model_name}")
    
    # Get LLM function with specified configuration
    try:
        llm_func = get_llm(api, model_name)
    except Exception as e:
        logging.exception(f"[KEYWORD_GEN] Failed to get LLM function for {api}/{model_name}: {e}")
        raise
    
    # Format prompt with the topic
    prompt = KEYWORDS_GENERATION_PROMPT.format(topic=topic)
    
    try:
        # Call the LLM function
        resp_msg = llm_func(prompt)
        if resp_msg.get("status") != "success":
            if "RESOURCE_EXHAUSTED" in resp_msg.get("message", ""):
                msg = "[KEYWORD_GEN] LLM resource exhausted; stopping further calls."
                logging.error(msg)
                raise RuntimeError(msg)
            msg = f"LLM call failed: {resp_msg.get('message', 'unknown error')}"
            logging.error(f"[KEYWORD_GEN] {msg}")
            raise RuntimeError(msg)
        
        # Extract text from response
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
        
    except Exception as e:
        logging.exception(f"[KEYWORD_GEN] Failed to generate keywords for topic={topic!r}: {e}")
        raise


@tool
def save_keywords_tool(topic: str, keywords: List[str], scope_list_path: str = None) -> str:
    """
    Save generated keywords to a JSON file.
    
    Args:
        topic: The research topic
        keywords: List of keywords to save
        scope_list_path: Path to save the keywords JSON file (optional)
        
    Returns:
        Confirmation message with save path
    """
    topic_key = (topic or "").strip().lower()
    if not topic_key:
        logging.warning("[KEYWORD_GEN] Empty topic; cannot save keywords.")
        return "Empty topic provided, no keywords saved."
    
    # Use default path if not provided
    if scope_list_path is None:
        scope_list_path = os.path.join("configs", "analysis_scope.json")
    
    new_set = {k.strip().lower() for k in (keywords or []) if isinstance(k, str) and k.strip()}
    if not new_set:
        logging.info("[KEYWORD_GEN] No valid keywords to save; skipping.")
        return "No valid keywords to save."
    
    path: Path = Path(scope_list_path)
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    
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
        return f"Successfully saved {len(merged)} keywords for topic '{topic_key}' to {path}"
    except Exception as e:
        logging.exception(f"[KEYWORD_GEN] Failed to save keywords: {e}")
        raise


class KeywordsGeneratorTool(BaseTool):
    """Langchain tool for generating and managing research keywords"""
    
    name: str = "keywords_generator"
    description: str = "Generate research keywords for a given topic and save them to a JSON file"
    scope_list_path: str = Field(default=os.path.join("configs", "analysis_scope.json"),
                               description="Path to save the keywords JSON file")
    api: str = Field(default="gemini", description="API to use for LLM calls")
    model_name: str = Field(default="gemini-2.5-flash", description="Model name for LLM calls")
    
    def _run(self, topic: str) -> Dict[str, Any]:
        """
        Generate keywords for a topic and save them automatically.
        
        Args:
            topic: The research topic to generate keywords for
            
        Returns:
            Dictionary with generated keywords and save status
        """
        try:
            # Generate keywords
            keywords = generate_keywords_tool(topic, self.model_name, self.api)
            
            # Save keywords
            save_result = save_keywords_tool(topic, keywords, self.scope_list_path)
            
            return {
                "status": "success",
                "keywords": keywords,
                "save_result": save_result,
                "keywords_count": len(keywords)
            }
            
        except Exception as e:
            logging.exception(f"[KEYWORD_GEN] Failed to process topic={topic!r}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _arun(self, topic: str) -> Dict[str, Any]:
        """Async version of the tool"""
        return self._run(topic)


# Export the tools for easy access
keywords_tools = [generate_keywords_tool, save_keywords_tool, KeywordsGeneratorTool()]