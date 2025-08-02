# paper_crawler.py
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any
import logging

def paper_matches_topic(
    paper: Dict[str, Any],
    topic_keywords: List[str],
    fields: List[str] = ["title"]
) -> bool:
    """
    Returns True if any of the topic_keywords appear (case-insensitive, as substring)
    in any of the specified fields of the paper dict.
    If topic_keywords is empty, returns True.
    Args:
        paper: Paper dictionary, should include 'title' and optionally 'abstract'.
        topic_keywords: List of keywords to search for.
        fields: List of fields in paper to search (e.g.: ["title", "abstract"])
    Returns:
        bool
    """
    if not topic_keywords:
        return True
    
    combined_text = ""
    for field in fields:
        value = paper.get(field, "")
        if isinstance(value, str):
            combined_text += " " + value.lower()
    if not combined_text.strip():
        return False  # Nothing to match
    
    for kw in topic_keywords:
        kw_lower = kw.lower().strip()
        if kw_lower and kw_lower in combined_text:
            return True
    return False

def download_pdf(pdf_url, save_path="temp/paper.pdf"):
    """
    Downloads a PDF from the given URL and saves it locally.
    Returns the save path if successful, or an error message (string starting with 'error: ...').
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(pdf_url, headers=headers, allow_redirects=True, timeout=30)
        resp.raise_for_status()
        if not resp.content.startswith(b'%PDF'):
            snippet = resp.content[:300].decode(errors='replace')
            return f"error: Not a valid PDF (possible HTML error page). File snippet: {snippet}"
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return "succeed"
    except requests.HTTPError as e:
        return f"error: HTTP error during download: {e} (status code: {getattr(e.response, 'status_code', None)})"
    except Exception as e:
        return f"error: Failed to download or save PDF: {e}"

def fetch_neurips_papers(year: int) -> List[Dict]:
    """
    Fetches NeurIPS papers for a given year from the public website.
    Returns a list of dictionaries, each containing 'title', 'authors', and 'url'.
    """
    BASE = "https://papers.nips.cc/paper_files"
    listing_url = f"{BASE}/paper/{year}"
    results = []
    seen_titles = set()

    try:
        resp = requests.get(listing_url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching NeurIPS listing for {year}: {e}")
        return results  # Empty list on error

    soup = BeautifulSoup(resp.text, "html.parser")

    for li in soup.find_all("li"):
        a = li.find("a", href=True)
        i = li.find("i")
        if not a or not i:
            continue

        paper_title = a.get_text(strip=True)
        if not paper_title or paper_title in seen_titles:
            continue  # Skip duplicates and empty titles
        seen_titles.add(paper_title)

        paper_url = urljoin(BASE + "/", a["href"])
        authors = [name.strip() for name in i.get_text().split(",") if name.strip()]

        results.append({
            "title": paper_title,
            "authors": authors,
            "paper_url": paper_url,
        })

    return results