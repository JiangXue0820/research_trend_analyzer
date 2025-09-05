from typing import Dict, Any, List, Optional, Literal
import re
import os

def make_response(
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

def ensure_parent_dir(db_path): 
    parent_dir = os.path.dirname(os.path.abspath(db_path)) 
    if parent_dir and not os.path.exists(parent_dir): 
        os.makedirs(parent_dir, exist_ok=True)

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

def safe_filename(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", (name or "").strip().lower())
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "paper"

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

def parse_markdown_summary(md_text: str) -> Dict:
    # 目标结构
    parsed = {
        "Paper Info": {"Title": "", "Authors": "", "Affiliations": ""},
        "Brief Summary": {"Highlight": "", "Keywords": ""},
        "Detailed Summary": {
            "1. Motivation": {"1.1 Background": "", "1.2 Problem Statement": ""},
            "2. State-of-the-Art Methods": {"2.1 Existing Methods": "", "2.2 Limitations of Existing Methods": ""},
            "3. Proposed Method": {"3.1 Main Contributions": "", "3.2 Core Idea": "", "3.3 Novelty": ""},
            "4. Experiment Results": {"4.1 Experimental Setup": "", "4.2 Experimental Results": ""},
            "5. Limitations and Future Work": {"5.1 Limitations": "", "5.2 Future Directions": ""},
        },
    }

    # parse Paper info code block
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", md_text, flags=re.S)
    md = next((b for b in code_blocks if "# Paper Info" in b), code_blocks[0] if code_blocks else md_text)

    # aggregate titles
    h1 = re.compile(r"^#\s+(.+?)\s*$")
    h2 = re.compile(r"^##\s+(.+?)\s*$")
    h3 = re.compile(r"^###\s+(.+?)\s*$")
    TOP = {"Paper Info", "Brief Summary", "Detailed Summary"}
    PI = {"Title", "Authors", "Affiliations"}
    BS = {"Highlight", "Keywords"}
    DS = {
        "1. Motivation": {"1.1 Background", "1.2 Problem Statement"},
        "2. State-of-the-Art Methods": {"2.1 Existing Methods", "2.2 Limitations of Existing Methods"},
        "3. Proposed Method": {"3.1 Main Contributions", "3.2 Core Idea", "3.3 Novelty"},
        "4. Experiment Results": {"4.1 Experimental Setup", "4.2 Experimental Results"},
        "5. Limitations and Future Work": {"5.1 Limitations", "5.2 Future Directions"},
    }

    # clean and connect
    CJK_PUNCT, OPENERS = "，。；：！？、）】》％%", "（【《“\"'([{" 

    def clean(s: str) -> str:
        s = re.sub(r":contentReference\[.*?\]\{.*?\}", "", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
        return s.replace("`", "").strip()

    def smart_join(a: str, b: str) -> str:
        b = clean(b)
        if not b: return a
        if not a: return b
        last, first = a[-1], b[0]
        glue = "" if (first in CJK_PUNCT or last in OPENERS or (last == "-" and first.isalpha())) else " "
        out = a + glue + b
        out = re.sub(r"\s+([{}])".format(CJK_PUNCT), r"\1", out)
        out = re.sub(r"\s+([)\]】》}])", r"\1", out)
        return re.sub(r"[ \t]+", " ", out).strip()

    # pointer
    cur_top = cur_pi_bs = cur_ds_grp = cur_ds_sub = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip(): continue

        if h1.match(line):
            t = h1.match(line).group(1).strip()
            cur_top = t if t in TOP else None
            cur_pi_bs = cur_ds_grp = cur_ds_sub = None
            continue
        if h2.match(line):
            sub = h2.match(line).group(1).strip()
            if cur_top == "Paper Info" and sub in PI:
                cur_pi_bs, cur_ds_grp, cur_ds_sub = sub, None, None
            elif cur_top == "Brief Summary" and sub in BS:
                cur_pi_bs, cur_ds_grp, cur_ds_sub = sub, None, None
            elif cur_top == "Detailed Summary" and sub in DS:
                cur_ds_grp, cur_ds_sub, cur_pi_bs = sub, None, None
            else:
                cur_pi_bs = cur_ds_sub = None
            continue
        if h3.match(line):
            subsub = h3.match(line).group(1).strip()
            cur_ds_sub = subsub if (cur_top == "Detailed Summary" and cur_ds_grp and subsub in DS[cur_ds_grp]) else None
            continue

        if cur_top == "Paper Info" and cur_pi_bs in PI:
            parsed["Paper Info"][cur_pi_bs] = smart_join(parsed["Paper Info"][cur_pi_bs], line)
        elif cur_top == "Brief Summary" and cur_pi_bs in BS:
            parsed["Brief Summary"][cur_pi_bs] = smart_join(parsed["Brief Summary"][cur_pi_bs], line)
        elif cur_top == "Detailed Summary" and cur_ds_grp and cur_ds_sub:
            parsed["Detailed Summary"][cur_ds_grp][cur_ds_sub] = smart_join(
                parsed["Detailed Summary"][cur_ds_grp][cur_ds_sub], line
            )

    return parsed
