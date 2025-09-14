"""
Utility functions for Research Trend Analyzer Agent.
Adapted for langchain framework compatibility with English comments.
"""

from .helper_func import (
    make_response,
    ensure_parent_dir,
    ensure_list,
    merge_unique_elements,
    strip_code_block,
    safe_filename,
    save_md_file,
    load_md_file,
    load_jsonl,
    save_jsonl,
    update_jsonl,
    parse_markdown_summary
)
from .call_llms import get_llm
from .paper_process import (
    paper_matches_topic,
    download_pdf,
    parse_pdf,
    delete_pdf,
    fetch_papers,
    fetch_neurips_papers,
    fetch_popets_papers,
    fetch_usenix_security_papers,
    fetch_usenix_soups_papers,
    fetch_acl_long_papers,
    fetch_acl_findings_papers
)
from .prompts import (
    KEYWORDS_GENERATION_PROMPT,
    PAPER_FILTER_PROMPT,
    PAPER_HIGHLIGHT_PROMPT,
    RESEARCH_TREND_PROMPT,
    PAPER_SUMMARY_PROMPT_CH,
    PAPER_SUMMARY_PROMPT_EN
)

__all__ = [
    # Helper functions
    'make_response',
    'ensure_parent_dir',
    'ensure_list',
    'merge_unique_elements',
    'strip_code_block',
    'safe_filename',
    'save_md_file',
    'load_md_file',
    'load_jsonl',
    'save_jsonl',
    'update_jsonl',
    'parse_markdown_summary',
    
    # LLM functions
    'get_llm',
    
    # Paper processing functions
    'paper_matches_topic',
    'download_pdf',
    'parse_pdf',
    'delete_pdf',
    'fetch_papers',
    'fetch_neurips_papers',
    'fetch_popets_papers',
    'fetch_usenix_security_papers',
    'fetch_usenix_soups_papers',
    'fetch_acl_long_papers',
    'fetch_acl_findings_papers',
    
    # Prompt templates
    'KEYWORDS_GENERATION_PROMPT',
    'PAPER_FILTER_PROMPT',
    'PAPER_HIGHLIGHT_PROMPT',
    'RESEARCH_TREND_PROMPT',
    'PAPER_SUMMARY_PROMPT_CH',
    'PAPER_SUMMARY_PROMPT_EN'
]