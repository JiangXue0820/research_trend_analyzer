import re

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
