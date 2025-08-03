# paper_crawler.py
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any
import logging

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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

    try:
        resp = requests.get(pdf_url, headers=HEADERS, allow_redirects=True, timeout=30)
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
    def html_to_pdf_link(html_url):
        if "-Abstract-Conference.html" in html_url:
            pdf_url = html_url.replace("/hash/", "/file/").replace("-Abstract-Conference.html", "-Paper-Conference.pdf")
        elif "-Abstract.html" in html_url:
            pdf_url = html_url.replace("/hash/", "/file/").replace("-Abstract.html", "-Paper.pdf")
        else:
            pdf_url = html_url
        return pdf_url

    BASE = "https://papers.nips.cc/paper_files"
    listing_url = f"{BASE}/paper/{year}"
    results = []
    seen_titles = set()

    try:
        resp = requests.get(listing_url, headers=HEADERS, allow_redirects=True, timeout=30)
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

        paper_url = html_to_pdf_link(urljoin(BASE + "/", a["href"]))
        authors = [name.strip() for name in i.get_text().split(",") if name.strip()]

        results.append({
            "title": paper_title.strip().lower(),
            "authors": authors,
            "paper_url": paper_url if paper_url else "",
        })

    return results


def fetch_aaai_papers(year: int) -> List[Dict]:
    BASE = "https://aaai.org/proceeding/aaai-39-2025/"
 
    try:
        resp = requests.get(BASE, headers=HEADERS, allow_redirects=True, timeout=30)
    except Exception as e:
        print(f"Error fetching NeurIPS listing for {year}: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find all <a> tags where href matches the issue URLs
    issue_urls = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if "ojs.aaai.org/index.php/AAAI/issue/view/" in href:
            issue_urls.append(href)

    results = []
    for iu in issue_urls:
        resp = requests.get(iu, headers=HEADERS, allow_redirects=True, timeout=30)

    # Find all articles in the issue
    for article_div in soup.select('.obj_article_summary'):
        # Extract title and URL
        title_tag = article_div.find('h3', class_='title').find('a')
        title = title_tag.text.strip()
        paper_url = title_tag['href']

        # Extract authors
        authors_div = article_div.find('div', class_='authors')
        authors = [a.strip() for a in authors_div.text.strip().split(',')]

        # Collect as dict
        results.append({
            'title': title,
            'authors': authors,
            'paper_url': paper_url
        })

    return results

    