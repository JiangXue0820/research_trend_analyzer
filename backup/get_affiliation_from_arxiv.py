#!/usr/bin/env python3
"""
arxiv_affiliation_extractor.py

Searches arXiv for a given paper title, downloads the PDF, and extracts affiliation lines from the first page.
"""

import re
import unicodedata
from pathlib import Path
import arxiv
import requests
from pdfminer.high_level import extract_text
from rapidfuzz import fuzz
import sys

# Keywords to identify affiliation lines
AFF_KEYWORDS = [
    "University", "Institute", "College",
    "Laboratory", "Centre", "Center", "School", "Department"
]

def normalize_title(title: str) -> str:
    # Convert curly quotes to straight
    t = title.replace("’", "'").replace("“", '"').replace("”", '"')
    # Strip accents/diacritics
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    # Remove punctuation except letters/numbers/spaces and quotes
    t = re.sub(r"[^0-9A-Za-z'\" ]+", " ", t)
    # Collapse multiple spaces
    return re.sub(r"\s+", " ", t).strip()

def fetch_arxiv_entry_exact(title: str):
    norm = normalize_title(title)
    search = arxiv.Search(
        query=f'ti:"{norm}"',
        max_results=1,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    return next(search.results(), None)

def search_fuzzy_on_arxiv(title: str, max_candidates: int = 5):
    norm = normalize_title(title)
    keywords = " ".join(norm.split()[:6])
    search = arxiv.Search(query=keywords, max_results=max_candidates)
    results = list(search.results())
    if not results:
        return None
    scored = [(fuzz.token_sort_ratio(title.lower(), r.title.lower()), r) for r in results]
    scored.sort(reverse=True, key=lambda x: x[0])
    top_score, top_result = scored[0]
    if top_score < 70:
        return None
    return top_result

def download_pdf(result, download_dir: Path = Path(".")) -> Path:
    pdf_url = result.pdf_url
    resp = requests.get(pdf_url)
    resp.raise_for_status()
    arxiv_id = result.entry_id.split("/")[-1]
    pdf_path = download_dir / f"temp.pdf"
    with open(pdf_path, "wb") as f:
        f.write(resp.content)
    print(f"✅ Downloaded PDF to {pdf_path}")
    return pdf_path

def extract_affiliations(pdf_path: Path) -> list[str]:
    text = extract_text(str(pdf_path), page_numbers=[0])
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        abs_idx = next(i for i, ln in enumerate(lines) if re.match(r"(?i)^abstract", ln))
    except StopIteration:
        abs_idx = len(lines)
    header = lines[1:abs_idx]
    affs = []
    for ln in header:
        if any(kw in ln for kw in AFF_KEYWORDS):
            affs.append(ln)
    return list(dict.fromkeys(affs))

def extract_affliation(title):
    print(f"Searching for: {title}")
    result = fetch_arxiv_entry_exact(title)
    if not result:
        print("Exact match not found, trying fuzzy search...")
        result = search_fuzzy_on_arxiv(title)
        if not result:
            print("❌ No suitable arXiv entry found.")
            sys.exit(1)
        print(f"Fuzzy match found: {result.title}")
    else:
        print(f"Exact match found: {result.title}")
    pdf_path = download_pdf(result)
    print("Extracting affiliations...")
    affiliations = extract_affiliations(pdf_path)
    if affiliations:
        print("Affiliations found:")
        for a in affiliations:
            print(f" - {a}")
    else:
        print("No affiliations detected.")

    return affiliations

