from typing import Dict, Any, List, Optional, Literal, Generator, Union
import re
import os
from pathlib import Path
import json
import logging

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
    s = (name or "").strip()
    s = "".join(c if c.isalnum() or c in ("-", "_", " ") else "_" for c in s)
    s = "_".join(s.split())[:180]  # collapse spaces, trim long names
    return s.lower() or "untitled"

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
            f"File loaded from {md_path}.",
            content
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
    
def load_jsonl(
    path: Union[str, Path],
    return_generator: bool = False
) -> Union[List[Dict[str, Any]], Generator[Dict[str, Any], None, None]]:
    """
    Load a JSONL (JSON Lines) file.

    Args:
        path: Path to the .jsonl file.
        return_generator: If True, return a generator (streaming).
                          If False, return a list (default).

    Returns:
        List[dict] or generator of dicts.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    def _iter_jsonl() -> Generator[Dict[str, Any], None, None]:
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        yield obj
                    else:
                        logging.warning(f"[JSONL] Skipping non-dict row at line {i} in {path}")
                except json.JSONDecodeError:
                    logging.warning(f"[JSONL] Skipping malformed line {i} in {path}")

    return _iter_jsonl() if return_generator else list(_iter_jsonl())


def save_jsonl(path: Union[str, Path], rows: List[Dict[str, Any]], append: bool = True) -> int:
    """
    Save rows to a JSONL file.

    Args:
        path: Path to the .jsonl file.
        rows: List of dict rows.
        append: If True, append to file; if False, overwrite.

    Returns:
        Number of rows actually written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    written = 0

    try:
        with path.open(mode, encoding="utf-8") as f:
            for row in rows:
                if not isinstance(row, dict):
                    logging.warning("[JSONL] Skipping non-dict row.")
                    continue
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
        logging.info(f"[JSONL] Wrote {written} rows to {path} (append={append})")
        return written
    except Exception as e:
        logging.exception(f"[JSONL] Failed to write {path}: {e}")
        return 0

    
def update_jsonl(path: Union[str, Path], rows: List[Dict[str, Any]]) -> int:
    """
    Update a JSONL file with new rows:
      - If the file exists: load, dedupe by full row content, then add new rows.
      - If not: create with the given rows.
      - Saves result back to the same path (overwrite).

    Args:
        path: Path to the .jsonl file.
        rows: List of dict rows to add.

    Returns:
        Number of new rows added.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    candidates = [r for r in rows if isinstance(r, dict)]
    if not candidates:
        logging.info(f"[JSONL] No valid rows to add to {path}")
        return 0

    # Load existing rows (if any)
    existing: List[Dict[str, Any]] = []
    if path.exists():
        try:
            existing = load_jsonl(path)  # list mode
        except Exception as e:
            logging.exception(f"[JSONL] Failed to read {path}: {e}")

    # Deduplicate using canonical JSON strings
    canon = lambda obj: json.dumps(obj, sort_keys=True, ensure_ascii=False)
    seen = {canon(r) for r in existing}

    added = 0
    for r in candidates:
        c = canon(r)
        if c not in seen:
            existing.append(r)
            seen.add(c)
            added += 1

    if added == 0:
        logging.info(f"[JSONL] No new rows to add for {path} (all duplicates).")
        return 0

    try:
        save_jsonl(path, existing, append=False)  # overwrite with deduped content
        logging.info(f"[JSONL] Updated {path} with {added} new rows (total {len(existing)})")
        return added
    except Exception as e:
        logging.exception(f"[JSONL] Failed to update {path}: {e}")
        return 0


def parse_markdown_summary(md_text: str) -> Dict:
    # validate input
    if not isinstance(md_text, str) or not md_text.strip():
        return make_response("error", "md_text must be a non-empty string.", None)

    try:
        # target structure
        parsed = {
            "Paper Info": {"Title": "", "Authors": "", "Affiliations": ""},
            "Brief Summary": {"Highlight": "", "Keywords": ""},
            "Detailed Summary": {
                "1. Motivation": {"1.1 Background": "", "1.2 Problem Statement": ""},
                "2. State-of-the-Art Methods": {
                    "2.1 Existing Methods": "",
                    "2.2 Limitations of Existing Methods": "",
                },
                "3. Proposed Method": {
                    "3.1 Main Contributions": "",
                    "3.2 Core Idea": "",
                    "3.3 Novelty": "",
                },
                "4. Experiment Results": {
                    "4.1 Experimental Setup": "",
                    "4.2 Experimental Results": "",
                },
                "5. Limitations and Future Work": {
                    "5.1 Limitations": "",
                    "5.2 Future Directions": "",
                },
            },
        }

        # parse Paper info code block
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", md_text, flags=re.S)
        md = next(
            (b for b in code_blocks if "# Paper Info" in b),
            code_blocks[0] if code_blocks else md_text,
        )

        # aggregate titles
        h1 = re.compile(r"^#\s+(.+?)\s*$")
        h2 = re.compile(r"^##\s+(.+?)\s*$")
        h3 = re.compile(r"^###\s+(.+?)\s*$")
        TOP = {"Paper Info", "Brief Summary", "Detailed Summary"}
        PI = {"Title", "Authors", "Affiliations"}
        BS = {"Highlight", "Keywords"}
        DS = {
            "1. Motivation": {"1.1 Background", "1.2 Problem Statement"},
            "2. State-of-the-Art Methods": {
                "2.1 Existing Methods",
                "2.2 Limitations of Existing Methods",
            },
            "3. Proposed Method": {
                "3.1 Main Contributions",
                "3.2 Core Idea",
                "3.3 Novelty",
            },
            "4. Experiment Results": {
                "4.1 Experimental Setup",
                "4.2 Experimental Results",
            },
            "5. Limitations and Future Work": {
                "5.1 Limitations",
                "5.2 Future Directions",
            },
        }

        # clean and connect
        CJK_PUNCT, OPENERS = "，。；：！？、）】》％%", "（【《“\"'([{" 

        def clean(s: str) -> str:
            try:
                s = re.sub(r":contentReference\[.*?\]\{.*?\}", "", s)
                s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
                return s.replace("`", "").strip()
            except re.error as e:
                # If a regex engine error occurs, fall back to a minimal clean
                return s.replace("`", "").strip()

        def smart_join(a: str, b: str) -> str:
            b = clean(b)
            if not b:
                return a
            if not a:
                return b
            last, first = a[-1], b[0]
            glue = "" if (first in CJK_PUNCT or last in OPENERS or (last == "-" and first.isalpha())) else " "
            out = a + glue + b
            try:
                out = re.sub(r"\s+([{}])".format(CJK_PUNCT), r"\1", out)
                out = re.sub(r"\s+([)\]】》}])", r"\1", out)
                return re.sub(r"[ \t]+", " ", out).strip()
            except re.error:
                # If post-joins regex fails, return a simple whitespace-normalized string
                return " ".join(out.split())

        # pointers
        cur_top = cur_pi_bs = cur_ds_grp = cur_ds_sub = None

        # guard: ensure md is string (it should be)
        if not isinstance(md, str):
            return make_response("error", "Failed to isolate markdown block.", None)

        for raw in md.splitlines():
            # robust line handling
            if not isinstance(raw, str):
                continue
            line = raw.rstrip()
            if not line.strip():
                continue

            m1 = h1.match(line)
            if m1:
                t = m1.group(1).strip()
                cur_top = t if t in TOP else None
                cur_pi_bs = cur_ds_grp = cur_ds_sub = None
                continue

            m2 = h2.match(line)
            if m2:
                sub = m2.group(1).strip()
                if cur_top == "Paper Info" and sub in PI:
                    cur_pi_bs, cur_ds_grp, cur_ds_sub = sub, None, None
                elif cur_top == "Brief Summary" and sub in BS:
                    cur_pi_bs, cur_ds_grp, cur_ds_sub = sub, None, None
                elif cur_top == "Detailed Summary" and sub in DS:
                    cur_ds_grp, cur_ds_sub, cur_pi_bs = sub, None, None
                else:
                    cur_pi_bs = cur_ds_sub = None
                continue

            m3 = h3.match(line)
            if m3:
                subsub = m3.group(1).strip()
                # guard DS indexing
                if cur_top == "Detailed Summary" and cur_ds_grp in DS and subsub in DS[cur_ds_grp]:
                    cur_ds_sub = subsub
                else:
                    cur_ds_sub = None
                continue

            # aggregate content with guards
            if cur_top == "Paper Info" and cur_pi_bs in PI:
                parsed["Paper Info"][cur_pi_bs] = smart_join(parsed["Paper Info"].get(cur_pi_bs, ""), line)
            elif cur_top == "Brief Summary" and cur_pi_bs in BS:
                parsed["Brief Summary"][cur_pi_bs] = smart_join(parsed["Brief Summary"].get(cur_pi_bs, ""), line)
            elif cur_top == "Detailed Summary" and cur_ds_grp in DS and cur_ds_sub in DS[cur_ds_grp]:
                parsed["Detailed Summary"][cur_ds_grp][cur_ds_sub] = smart_join(
                    parsed["Detailed Summary"][cur_ds_grp].get(cur_ds_sub, ""),
                    line,
                )
            else:
                # line outside recognized sections — ignore gracefully
                continue

        # success
        return make_response("success", "Parsed markdown summary.", parsed)

    except re.error as e:
        return make_response("error", f"Regex error while parsing: {e}", None)
    except Exception as e:
        return make_response("error", f"Failed to parse markdown summary: {e}", None)
