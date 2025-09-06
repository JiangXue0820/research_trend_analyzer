# paper_crawler.py
import os
import requests
import fitz
import re
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any, Union, Optional
from utils.helper_func import *


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


# Compile once
ACK_PAT = re.compile(r"^\s*acknowledg(e)?ment(s)?\s*$", re.IGNORECASE)
REF_PAT = re.compile(r"^\s*(references?|bibliography|works\s+cited)\s*$", re.IGNORECASE)

def validate_pdf_path(pdf_path: str) -> None:
    if not isinstance(pdf_path, str) or not pdf_path.strip():
        raise ValueError("pdf_path must be a non-empty string.")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if not os.path.isfile(pdf_path):
        raise ValueError(f"Not a file: {pdf_path}")
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError("The provided path does not have a .pdf extension.")

def parse_pdf(
    pdf_path: str,
    include_anchor_page: bool = False, 
    early_stop: bool = True,
):
    """
    Extract text from the PDF. By default, stops BEFORE the first line that looks like an
    'Acknowledgments' or 'References' heading (case-insensitive, whole-line match) and
    EXCLUDES that heading and everything after it on that page.

    Args:
        pdf_path (str): The path to the PDF file.
        include_anchor_page (bool): Whether to also include the content of anchor page in the output.
        early_stop (bool): Whether to stop parsing at the first acknowledgment or reference section.
    """
    try:
        validate_pdf_path(pdf_path)
    except Exception as e:
        return make_response("error", str(e), None)

    try:
        with fitz.open(pdf_path) as doc:
            page_count = doc.page_count
            if page_count == 0:
                return make_response("warning", "Empty PDF (0 pages).", None)

            # If not stopping early, return the entire document text
            if not early_stop:
                try:
                    text = "".join(doc[pno].get_text("text") for pno in range(page_count))
                except Exception as e:
                    return make_response("error", f"Failed to extract text: {e}", None)
                return make_response("success", f"Parsed {page_count} page(s).", text)

            # early_stop=True: stop at first matching heading
            parts = []
            stop_section: Optional[str] = None
            stop_page: Optional[int] = None

            for pno in range(page_count):
                try:
                    page_text = doc[pno].get_text("text")
                except Exception as e:
                    return make_response("error", f"Failed to read page {pno}: {e}", None)

                lines = page_text.splitlines()

                hit_idx = None
                hit_label = None
                for i, ln in enumerate(lines):
                    if ACK_PAT.match(ln):
                        hit_idx, hit_label = i, "acknowledgments"
                        break
                    if REF_PAT.match(ln):
                        hit_idx, hit_label = i, "references"
                        break

                if hit_idx is None:
                    parts.append(page_text)
                    continue

                # Found a stop section on this page
                stop_section = hit_label
                stop_page = pno

                if include_anchor_page:
                    # Include entire anchor page, then stop
                    parts.append(page_text)
                else:
                    # EXCLUDE the heading and everything after it on this page
                    before = "\n".join(lines[:hit_idx]).rstrip()
                    parts.append(before)

                break  # stop after handling the anchor page

            text_out = "\n".join(parts).strip() if parts else None

            if stop_section is not None and stop_page is not None:
                return make_response(
                    "success",
                    f"Stopped at {stop_section} on page {stop_page}",
                    text_out,
                )
            else:
                # No stop section found — return everything read
                return make_response(
                    "success",
                    "Reached end of document without finding a stop section.",
                    text_out,
                )

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
    
class BaseFetcher(ABC):
    SITE: str = "Base"
    HEADERS: Dict = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def fetch(self, year: int) -> Dict[str, Any]:
        """Public API: validate → scrape → wrap in make_response."""
        try:
            y = self._validate_year(year)
            data = self._scrape(y, self.HEADERS)
            if not data:
                return make_response("success", f"No papers found for {self.SITE} {y}.", [])
            return make_response("success", f"Fetched {len(data)} papers from {self.SITE} {y}.", data)
        except Exception as e:
            return make_response("error", f"{self.SITE} error: {e}", None)

    # -------- hooks for subclasses --------
    @abstractmethod
    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        ...

    # -------- shared utilities --------
    def _validate_year(self, year: int) -> int:
        try:
            y = int(year)
        except Exception:
            raise ValueError("year must be an integer.")
        if not (1900 <= y <= 2100):
            raise ValueError(f"year out of expected range: {y}.")
        return y

    def _fetch_html(self, url: str, headers: Dict[str, str], label: str, timeout: int = 30) -> str:
        try:
            import requests
        except Exception as e:
            raise RuntimeError(f"Missing dependency 'requests': {e}")
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True, timeout=timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"Network error fetching {label}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error fetching {label}: {e}")
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} fetching {url}")
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" not in ctype:
            logging.warning("Expected HTML but got Content-Type=%s for %s", ctype, url)
        return resp.text

    def _soup(self, html: str):
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            raise RuntimeError(f"Missing dependency 'beautifulsoup4': {e}")
        try:
            return BeautifulSoup(html, "html.parser")
        except Exception as e:
            raise RuntimeError(f"Failed to parse HTML: {e}")

    def _split_authors(self, text: str) -> List[str]:
        parts = re.split(r",|\band\b", text or "", flags=re.IGNORECASE)
        return [re.sub(r"\s+", " ", p).strip().title() for p in parts if p and p.strip()]

    # Optional override per site
    def _html_to_pdf_link(self, url: str) -> str:
        return url or ""


# ------------------------- NeurIPS -------------------------

class NeuripsFetcher(BaseFetcher):
    SITE = "NeurIPS"
    BASE = "https://papers.nips.cc/paper_files"

    def _html_to_pdf_link(self, url: str) -> str:
        u = url or ""
        try:
            if "-Abstract-Conference.html" in u:
                return u.replace("/hash/", "/file/").replace("-Abstract-Conference.html", "-Paper-Conference.pdf")
            if "-Abstract.html" in u:
                return u.replace("/hash/", "/file/").replace("-Abstract.html", "-Paper.pdf")
        except Exception:
            pass
        return u

    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        listing_url = f"{self.BASE}/paper/{year}"
        html = self._fetch_html(listing_url, headers, f"{self.SITE} listing for {year}")
        soup = self._soup(html)

        results: List[Dict[str, Any]] = []
        seen = set()

        items = soup.find_all("li")
        for li in items:
            try:
                a = li.find("a", href=True)
                i = li.find("i")
                if not a or not i:
                    continue

                title = (a.get_text(strip=True) or "").strip()
                if not title or title in seen:
                    continue
                seen.add(title)

                href = a.get("href", "")
                html_url = urljoin(self.BASE + "/", href) if href else ""
                paper_url = self._html_to_pdf_link(html_url)
                authors = self._split_authors(i.get_text())

                results.append({
                    "title": title.strip().title(),
                    "authors": authors,
                    "paper_url": paper_url or "",
                })
            except Exception as e:
                logging.warning("Skipping one NeurIPS entry: %s", e)
        return results


# ------------------------- AAAI -------------------------

class AAAIFetcher(BaseFetcher):
    SITE = "AAAI"
    BASE = "https://aaai.org/proceeding/aaai-39-2025/"  # kept as in your code

    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        base_html = self._fetch_html(self.BASE, headers, f"{self.SITE} listing for {year}")
        base_soup = self._soup(base_html)

        issue_urls: List[str] = []
        for a in base_soup.find_all("a", href=True):
            href = a["href"]
            if "ojs.aaai.org/index.php/AAAI/issue/view/" in href:
                issue_urls.append(urljoin(self.BASE, href))

        results: List[Dict[str, Any]] = []
        seen = set()

        def parse_issue(html: str) -> None:
            s = self._soup(html)
            for art in s.select(".obj_article_summary"):
                try:
                    h3 = art.find("h3", class_="title")
                    a = h3.find("a", href=True) if h3 else None
                    if not a:
                        continue
                    title = (a.text or "").strip()
                    if not title or title in seen:
                        continue
                    seen.add(title)

                    paper_url = urljoin(self.BASE, a["href"])
                    authors_div = art.find("div", class_="authors")
                    authors = self._split_authors(authors_div.get_text(" ", strip=True) if authors_div else "")

                    results.append({
                        "title": title.strip().title(),
                        "authors": authors,
                        "paper_url": paper_url,
                    })
                except Exception as e:
                    logging.warning("Skipping one AAAI entry: %s", e)

        if issue_urls:
            for iu in issue_urls:
                try:
                    html = self._fetch_html(iu, headers, f"{self.SITE} issue page for {year}")
                    parse_issue(html)
                except Exception as e:
                    logging.warning("Issue fetch failed (%s): %s", iu, e)
        else:
            parse_issue(base_html)

        return results


# ------------------------- Public entry points -------------------------

def fetch_neurips_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return NeuripsFetcher().fetch(year)

def fetch_aaai_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return AAAIFetcher().fetch(year)

def fetch_papers(venue: str, year: int) -> Dict[str, Any]:
    """Generic factory-based fetch, returns make_response(...)."""
    registry = {
        "neurips": NeuripsFetcher(),
        "aaai": AAAIFetcher(),
    }
    f = registry.get((venue or "").lower())
    if not f:
        return make_response("error", f"Unknown venue: {venue}. Try: {registry.keys()}", None)
    return f.fetch(year)