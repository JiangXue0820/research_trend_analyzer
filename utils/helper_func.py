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