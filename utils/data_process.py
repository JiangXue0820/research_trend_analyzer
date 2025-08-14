import re
import sqlite3
import os
from typing import Dict, Any, List, Optional, Literal


def _make_response(
    status: Literal["success", "warning", "error"],
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construct structured return message：
    {
        "status": "success" | "warning" | "error",
        "message": "描述信息",
        "data": {...} | None
    }
    """
    return {"status": status, "message": message, "data": data}



def ensure_parent_dir(path: str) -> Dict[str, Any]:
    """
    Ensure the parent directory of the given path exists; create it if missing.

    Args:
        path (str): A file path whose parent directory should exist.
    """
    parent_dir = os.path.dirname(os.path.abspath(path))
    if not parent_dir:
        return _make_response(
            "warning",
            "No parent directory resolved from the given path.",
            {"parent_dir": "", "created": False}
        )

    if os.path.exists(parent_dir):
        return _make_response(
            "success",
            "Parent directory already exists.",
            {"parent_dir": parent_dir, "created": False}
        )

    try:
        os.makedirs(parent_dir, exist_ok=True)
        return _make_response(
            "success",
            "Parent directory created.",
            {"parent_dir": parent_dir, "created": True}
        )
    except Exception as e:
        return _make_response(
            "error",
            f"Failed to create parent directory: {e}",
            None
        )
    

def save_md_file(text: str, md_path: str, mode: str = "w") -> Dict[str, Any]:
    """
    Save markdown text to a file.

    Args:
        text (str): The markdown-formatted text to save.
        md_path (str): Output file path (should end with .md).
        mode (str, optional): File mode, "w" to overwrite, "a" to append. Default is "w".
    """
    ensure_resp = ensure_parent_dir(md_path)
    if ensure_resp["status"] == "error":
        return _make_response("error", f"Cannot ensure parent dir: {ensure_resp['message']}", None)

    try:
        with open(md_path, mode, encoding="utf-8") as f:
            written = f.write(text)
        return _make_response(
            "success",
            "Markdown saved.",
            {"path": md_path, "mode": mode, "bytes_written": written}
        )
    except Exception as e:
        return _make_response(
            "error",
            f"Failed to save markdown: {e}",
            None
        )
    
def load_md_file(md_path: str) -> Dict[str, Any]:
    """
    Load the contents of a Markdown (.md) file.

    Args:
        md_path (str): Path to the markdown file.
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        return _make_response(
            "success",
            "File loaded.",
            {"path": md_path, "content": content}
        )
    except FileNotFoundError:
        return _make_response(
            "warning",
            f"File not found: {md_path}",
            None
        )
    except Exception as e:
        return _make_response(
            "error",
            f"Failed to load markdown: {e}",
            None
        )
    

def get_md_section(content: str, section_name: str, level: int = 2) -> Dict[str, Any]:
    """
    Extract a Markdown section by header text.

    Args:
        content (str): Full markdown content.
        section_name (str): Name of the section to extract (case-insensitive, no '#').
        level (int, optional): Header level to match (1='#', 2='##', ...). Default 2.
    """
    try:
        pattern = (
            rf"^{'#' * level}\s*{re.escape(section_name)}\s*\n"  # header line
            rf"(.*?)"                                            # section body (non-greedy)
            rf"(?=^#{{1,{level}}}\s|\Z)"                         # next header (level <= given) or EOF
        )
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not match:
            return _make_response(
                "warning",
                f"Section '{section_name}' not found.",
                None
            )
        return _make_response(
            "success",
            "Section '{section_name}' extracted.",
            {"section": match.group(1).strip(), "section_name": section_name, "level": level}
        )
    except Exception as e:
        return _make_response(
            "error",
            f"Failed to extract section: {e}",
            None
        )
    

def initialize_paper_database(paper_db_path: str) -> Dict[str, Any]:
    """
    Initialize (create if not exists) the SQLite paper database and table.

    Args:
        paper_db_path (str): Path to the SQLite database file.
    """
    ensure_resp = ensure_parent_dir(paper_db_path)
    if ensure_resp["status"] == "error":
        return _make_response("error", f"Cannot ensure parent dir: {ensure_resp['message']}", None)

    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                conference TEXT,
                year INTEGER,
                paper_url TEXT,
                topic TEXT,
                keywords TEXT
            );
            """
        )
        conn.commit()
        conn.close()
        return _make_response(
            "success",
            "Table created or already existed.",
            {"path": paper_db_path, "created_or_checked": True}
        )
    except Exception as e:
        return _make_response(
            "error",
            f"[CREATE_TABLE] Failed to create/check table: {e}",
            None
        )


def ensure_list(val):
    if isinstance(val, list):
        return val
    return [val] if val else []

def merge_unique_elements(list1, list2):
    list1 = ensure_list(list1)
    list2 = ensure_list(list2)
    
    seen = set()
    result = []
    for item in list1 + list2:
        key = item.lower() if isinstance(item, str) else item
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

def strip_code_block(text: str) -> str:
    # Removes ```json, ```python, or just ``` ... ```
    code_block_pattern = r"^```(?:json|python)?\s*([\s\S]+?)\s*```$"
    match = re.match(code_block_pattern, text.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()