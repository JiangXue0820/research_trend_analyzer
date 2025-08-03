import re
import sqlite3
import os

def ensure_parent_dir(db_path):
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    

def save_md_file(text: str, md_path: str, mode: str = "w") -> str:
    """
    Save the given text to a markdown (.md) file.
    
    Args:
        text: The markdown-formatted text to save.
        md_path: Output file path (should end with .md).
        mode: File mode, "w" to overwrite, "a" to append. Default is "w".
    Returns:
        The path of the saved file, or an error message if failed.
    """
    try:
        with open(md_path, mode, encoding="utf-8") as f:
            f.write(text)
        return {"message": f"Markdown saved to {md_path}"}
    except Exception as e:
        return {"error": f"Failed to save markdown: {e}"}
    
def load_md_file(md_path: str) -> str:
    """
    Load and return the contents of a markdown (.md) file.

    Args:
        md_path: Path to the markdown file.
    Returns:
        The file content as a string, or an error message if failed.
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "message": f"file loaded from {md_path}",
            "content": content
            }
    except FileNotFoundError:
        return {"error": f"File {md_path} not found."}
    except Exception as e:
        return {"error": f"Failed to load markdown: {e}"}
    

def get_md_section(content: str, section_name: str, level: int = 2) -> dict:
    """
    Extracts a Markdown section (by header) from a file.
    Args:
        md_path: Path to the markdown file.
        section_name: Name of the section to extract (case-insensitive, no #).
        level: Header level (e.g., 1 for #, 2 for ##, etc.). Default: 2 (## Section).
    Returns:
        dict: {"section": section_text} or {"error": "..."}
    """
    try:
        # Build regex pattern for the section header and next header
        # E.g. for level 2: '^## Section Name' (case-insensitive)
        pattern = (
            rf"^{'#' * level}\s*{re.escape(section_name)}\s*\n"    # Match header
            rf"(.*?)"                                              # Capture everything after header (non-greedy)
            rf"(?=^#{{1,{level}}}\s|\Z)"                           # Stop at next header of level <= given, or EOF
        )
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not match:
            return {"error": f"Section '{section_name}' not found."}
        return {
            "message": f"section {section_name} extracted",
            "section": match.group(1).strip()
        }
    except Exception as e:
        return {"error": f"Failed to extract section: {e}"}
    

def initialize_paper_database(paper_db_path: str):
    try:
        ensure_parent_dir(paper_db_path)
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        cursor.execute('''
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
        ''')
        conn.commit()
        conn.close()
        return {"message": f"Created or checked table in {paper_db_path}"}
    except Exception as e:
        return {"error": f"[CREATE_TABLE] Failed to create/check table in {paper_db_path}: {e}"}

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