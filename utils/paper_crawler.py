# paper_crawler.py
import os
import requests
import pymupdf
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any, Union, Optional
from utils.helper_func import *

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
    keywords: List[str],
    fields: List[str] = ["title"]
) -> Dict[str, Any]:
    """
    Check if any topic keywords appear (case-insensitive, substring match)
    in the specified fields of a paper dictionary.

    Args:
        paper (dict): Dictionary containing paper information (e.g., title, abstract).
        keywords (list[str]): Keywords to search for.
        fields (list[str], optional): Fields to search in. Defaults to ["title"].

    """
    try:
        if not keywords:
            # TODO: warning or error?
            return make_response(
                "warning",
                "No topic keywords provided — cannot check for topic match.",
                None
            )

        # Combine text from specified fields into one lowercase string
        combined_text = ""
        for field in fields:
            value = paper.get(field, "")
            if isinstance(value, str):
                combined_text += " " + value.lower()

        if not combined_text.strip():
            # TODO: warning or error?
            return make_response(
                "warning",
                "No text found in specified fields — cannot check for topic match.",
                None
            )

        # Find all matching keywords (case-insensitive, substring match)
        matched_keywords: List[str] = []
        seen = set()  # de-duplicate while preserving order
        for kw in keywords:
            if not isinstance(kw, str):
                continue
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            if kw_lower in combined_text and kw not in seen:
                matched_keywords.append(kw)  # keep original form for readability
                seen.add(kw)

        if matched_keywords:
            return make_response(
                "success",
                "Keyword matches found.",
                {"matched": True, "keywords": matched_keywords, "fields": fields}
            )

        return make_response(
            "warning",
            "No matching keywords found in specified fields.",
            {"matched": False, "keywords": [], "fields": fields}
        )

    except Exception as e:
        return make_response(
            "error",
            f"Error while checking topic match: {e}",
            None
        )

    except Exception as e:
        return make_response(
            "error",
            f"Error while checking topic match: {e}",
            None
        )
    
def download_pdf(pdf_url: str, paper_path: str):
    """
    Downloads a PDF from the given URL and saves it locally.
    Returns the save path if successful, or an error message (string starting with 'error: ...').

    Args:
        pdf_url (str): The URL pointing to the PDF file.
        paper_path (str, optional): Local file path to save the PDF. Defaults to "temp/paper.pdf".

    """
    if not isinstance(pdf_url, str) or not pdf_url.strip():
        return make_response("error", 
                             "No pdf_url provided.", 
                             None)
    
    if not isinstance(paper_path, str) or not paper_path.strip():
        return make_response("error", 
                             "No paper_path provided.", 
                             None)

    ensure_parent_dir(paper_path)

    try:
        resp = requests.get(pdf_url, headers=HEADERS, allow_redirects=True, timeout=30)
        resp.raise_for_status()
        if not resp.content.startswith(b"%PDF"):
            snippet = resp.content[:300].decode(errors="replace")
            return make_response("error", 
                                 f"Not a valid PDF (possible HTML page). Snippet: {snippet}",
                                 None)
        
        with open(paper_path, "wb") as f:
            f.write(resp.content)
        return make_response("success", 
                             "Downloaded PDF successfully.",
                              {"pdf_url": pdf_url, "path": paper_path, "bytes": len(resp.content)})
    
    except requests.HTTPError as e:
        return make_response("error",
                             f"HTTP error while downloading PDF: {e} (status code: {getattr(e.response, 'status_code', None)})",
                             None)
    
    except Exception as e:
        return make_response("error", f"Failed to download or save PDF: {e}", None)


def parse_pdf(paper_path: str):
    """
        Parse text from a local PDF at `paper_path`, and return the text. 

        Args:
            paper_path (str): Absolute or relative path to the PDF file on disk.
    """
    if not isinstance(paper_path, str) or not paper_path.strip():
        return make_response("error", "No paper_path provided.", None)

    try:
        with pymupdf.open(paper_path) as doc:
            text = "".join(page.get_text() for page in doc)
            page_count = doc.page_count
        return make_response("success", f"Parsed {page_count} page(s).",
                                         {"text": text, "page_count": page_count})
    except Exception as e:
        return make_response("error", f"Failed to parse PDF: {e}", None)

    
def delete_pdf(paper_path="temp/paper.pdf"):
    """
    Deletes the temporary PDF according to the file path.
    Always returns a dict with 'message_type' and 'message_content'.

    Args:
        paper_path (str, optional): Path to the PDF file. Defaults to "temp/paper.pdf"
    """
    try:
        if os.path.exists(paper_path):
            os.remove(paper_path)
            return make_response(
                "success",
                "Deleted PDF successfully.",
                {"deleted": True, "path": paper_path}
            )
        else:
            return make_response(
                "warning",
                "No PDF found at the given path; nothing to delete.",
                None
            )
    except Exception as e:
        return make_response(
            "error",
            f"Could not delete PDF: {e}",
            None
        )
    
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

        title = a.get_text(strip=True)
        if not title or title in seen_titles:
            continue  # Skip duplicates and empty titles
        seen_titles.add(title)

        paper_url = html_to_pdf_link(urljoin(BASE + "/", a["href"]))
        authors = [name.strip().title() for name in i.get_text().split(",") if name.strip()]

        results.append({
            "title": title.strip().title(),
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
        authors = [a.strip().title() for a in authors_div.text.strip().split(',')]

        # Collect as dict
        results.append({
            'title': title.strip().title(),
            'authors': authors,
            'paper_url': paper_url
        })

    return results

    