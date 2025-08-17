import sqlite3
import os

from utils.helper_func import *
    

def save_md_file(text: str, md_path: str, mode: str = "w") -> Dict[str, Any]:
    """
    Save markdown text to a file.

    Args:
        text (str): The markdown-formatted text to save.
        md_path (str): Output file path (should end with .md).
        mode (str, optional): File mode, "w" to overwrite, "a" to append. Default is "w".
    """
    ensure_parent_dir(md_path)

    try:
        with open(md_path, mode, encoding="utf-8") as f:
            written = f.write(text)
        return make_response(
            "success",
            "Markdown saved.",
            {"path": md_path, "mode": mode, "bytes_written": written}
        )
    except Exception as e:
        return make_response(
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
        return make_response(
            "success",
            "File loaded.",
            {"path": md_path, "content": content}
        )
    except FileNotFoundError:
        return make_response(
            "warning",
            f"File not found: {md_path}",
            None
        )
    except Exception as e:
        return make_response(
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
            return make_response(
                "warning",
                f"Section '{section_name}' not found.",
                None
            )
        return make_response(
            "success",
            "Section '{section_name}' extracted.",
            {"section": match.group(1).strip(), "section_name": section_name, "level": level}
        )
    except Exception as e:
        return make_response(
            "error",
            f"Failed to extract section: {e}",
            None
        )
    

def initialize_paper_database(paper_db_path: str) -> Dict[str, Any]:
    """
    Initialize (create if not exists) the SQLite paper database and indexes.
    Ensures case-insensitive (NOCASE) comparisons for title, conference, topic, keywords,
    and creates indexes optimized for typical queries.
    """
    ensure_parent_dir(paper_db_path)

    try:
        conn = sqlite3.connect(paper_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")  # 习惯性打开外键（即使当前表未使用）

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT COLLATE NOCASE,
                authors    TEXT,
                conference TEXT COLLATE NOCASE,
                year       INTEGER,
                paper_url  TEXT,
                topic      TEXT COLLATE NOCASE,
                keywords   TEXT COLLATE NOCASE
            );
            """
        )

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_conf_year_topic_nocase
            ON papers(conference COLLATE NOCASE, year, topic COLLATE NOCASE);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title_nocase
            ON papers(title COLLATE NOCASE);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_keywords_nocase
            ON papers(keywords COLLATE NOCASE);
        """)

        conn.commit()
        conn.close()
        return make_response(
            "success",
            "Table and case-insensitive indexes created or already existed.",
            {"path": paper_db_path, "created_or_checked": True}
        )
    except Exception as e:
        return make_response(
            "error",
            f"[CREATE_TABLE] Failed to create/check table or indexes: {e}",
            None
        )