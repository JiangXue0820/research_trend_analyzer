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
from tqdm import tqdm


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
        for li in tqdm(items, f"Fetching NeurIPS {year} papers"):
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


# ------------------------- PETS -------------------------

class PoPETsFetcher(BaseFetcher):
    SITE = "PoPETs"
    BASE = "https://petsymposium.org/popets"

    def _toc_url(self, year: int) -> str:
        return f"{self.BASE}/{year}/"

    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        toc = self._toc_url(year)
        html = self._fetch_html(toc, headers, f"{self.SITE} {year} listing")
        soup = self._soup(html)

        results: List[Dict[str, Any]] = []

        for li in soup.select("li"):
            try:
                a_tags = li.select("a[href]")
                if not a_tags:
                    continue

                # ---- choose title anchor (not PDF / not nav / not roots)
                def is_title_anchor(a):
                    t = (a.get_text(strip=True) or "").strip()
                    h = (a.get("href") or "").strip()
                    if not t or t.lower() in {"pdf", "home", "proceedings"}:
                        return False
                    if h.lower().endswith(".pdf"):
                        return False
                    bad_roots = {
                        "https://petsymposium.org/",
                        "https://petsymposium.org/popets/",
                        "/popets/",
                        "/",
                    }
                    if h in bad_roots:
                        return False
                    return True

                title_a = next((a for a in a_tags if is_title_anchor(a)), None)
                if not title_a:
                    continue

                title = (title_a.get_text(strip=True) or "").strip()
                if title.lower() in {"home", "proceedings"}:
                    continue

                # ---- pick PDF link (if missing, derive from article link)
                pdf_a = next(
                    (a for a in a_tags
                     if (a.get_text(strip=True) or "").upper() == "PDF"
                     or (a.get("href") or "").lower().endswith(".pdf")),
                    None
                )
                if pdf_a:
                    paper_url = urljoin(toc, pdf_a.get("href") or "")
                else:
                    href = title_a.get("href") or ""
                    paper_url = urljoin(toc, href[:-4] + "pdf") if href.lower().endswith(".php") else urljoin(toc, href)

                # Filter out invalid roots defensively
                if paper_url in ("https://petsymposium.org/", "https://petsymposium.org/popets/"):
                    continue

                # ---- authors: take DOM text *after* the PDF anchor; fallback to split('PDF')
                authors_text = ""
                if pdf_a is not None:
                    parts = []
                    for sib in pdf_a.next_siblings:
                        # include text in following siblings (strings or tags)
                        if getattr(sib, "get_text", None):
                            parts.append(sib.get_text(" ", strip=True))
                        else:
                            s = str(sib).strip()
                            if s:
                                parts.append(s)
                    authors_text = " ".join(parts)
                if not authors_text:
                    # fallback: everything after 'PDF'
                    raw = li.get_text(" ", strip=True)
                    authors_text = re.split(r"\bPDF\b", raw, flags=re.I)[-1]

                # cleanup
                authors_text = re.sub(r"^\s*[\]\)\-–—:|]+", " ", authors_text)           # trim leading ] ) : -
                authors_text = re.sub(r"\[[^\]]*\]", " ", authors_text)                  # drop bracketed tokens
                authors_text = re.sub(r"\([^)]*\)", " ", authors_text)                   # drop affiliations
                authors_text = re.sub(r"\b(Artifact|Artifacts?|Code|Dataset|Video|Slides|Source|Supplementary)\b.*$", " ", authors_text, flags=re.I)
                authors_text = re.sub(r"\s+", " ", authors_text).strip(" ,;:-")

                authors = [re.sub(r"\s+", " ", s).strip(" ,;") for s in re.split(r",|;|\band\b", authors_text, flags=re.I) if s.strip()]

                results.append({"title": title, "authors": authors, "paper_url": paper_url})
            except Exception as e:
                logging.warning("Skipping one PoPETs entry: %s", e)

        return results

# ------------------------- USENIX-------------------------

class UsenixSecurityFetcher(BaseFetcher):
    SITE = "USENIX Security"
    BASE = "https://www.usenix.org"

    def _sessions_url(self, year: int) -> str:
        yy = f"{year % 100:02d}"
        return f"{self.BASE}/conference/usenixsecurity{yy}/technical-sessions"

    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        # 1) collect presentation page URLs for the year
        sessions_url = self._sessions_url(year)
        html = self._fetch_html(sessions_url, headers, f"{self.SITE} technical sessions {year}")
        soup = self._soup(html)

        yy = f"{year % 100:02d}"
        pres_links = []
        for a in soup.select(f'a[href*="/conference/usenixsecurity{yy}/presentation/"]'):
            href = a.get("href")
            if href:
                pres_links.append(urljoin(sessions_url, href))
        pres_links = sorted(set(pres_links))

        # 2) parse each presentation page for title, authors, pdf
        results: List[Dict[str, Any]] = []
        for url in tqdm(pres_links, f"Fetching USENIX {year} papers"):
            try:
                phtml = self._fetch_html(url, headers, "presentation page")
                psoup = self._soup(phtml)

                # title
                h1 = psoup.find("h1")
                title = (h1.get_text(strip=True) if h1 else "").strip()
                if not title:
                    continue

                # authors (prefer meta tags; fallback to BibTeX)
                authors = [m.get("content").strip() for m in psoup.select('meta[name="citation_author"]') if m.get("content")]
                if not authors:
                    # try BibTeX: author = {A and B and C}
                    m = re.search(r"author\s*=\s*\{([^}]+)\}", psoup.get_text("\n", strip=True), flags=re.IGNORECASE | re.DOTALL)
                    if m:
                        authors = [a.strip() for a in m.group(1).split(" and ") if a.strip()]

                # pdf url (skip slides if both exist)
                pdf_url = ""
                for a in psoup.select('a[href$=".pdf"], a[href*=".pdf?"]'):
                    href = a.get("href") or ""
                    if href:
                        cand = urljoin(url, href)
                        name = cand.lower()
                        if "slides" in name or "talk" in name:
                            continue
                        pdf_url = cand
                        break
                if not pdf_url:
                    continue

                results.append({"title": title, "authors": authors, "paper_url": pdf_url})
            except Exception as e:
                logging.warning("Skipping one presentation (%s): %s", url, e)

        return results
    
class UsenixSoupsFetcher(BaseFetcher):
    SITE = "USENIX SOUPS"
    BASE = "https://www.usenix.org"

    def _sessions_url(self, year: int) -> str:
        return f"{self.BASE}/conference/soups{year}/technical-sessions"

    def _parse_authors(self, page_text: str) -> List[str]:
        # Grab text after "Authors:" up to "Abstract:" or "Open Access Media"
        m = re.search(r"Authors:\s*(.*?)\s*(Abstract:|Open Access Media|$)",
                      page_text, flags=re.I | re.S)
        chunk = m.group(1) if m else ""
        # Strip affiliations in parentheses/brackets; normalize separators
        chunk = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", chunk)
        chunk = re.sub(r"\s+and\s+", ",", chunk, flags=re.I)
        # Split and keep person-like tokens
        names = [re.sub(r"\s+", " ", s).strip(" ,;:-") for s in chunk.split(",")]
        names = [n for n in names if n and len(n.split()) >= 2]
        return names

    def _pick_pdf(self, soup, base_url: str) -> str:
        # Prefer first .pdf that doesn't look like slides
        for a in soup.select('a[href$=".pdf"], a[href*=".pdf?"]'):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            cand = urljoin(base_url, href)
            if "slides" in cand.lower():
                continue
            return cand
        return ""

    def _scrape(self, year: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        sessions = self._sessions_url(year)
        soup = self._soup(self._fetch_html(sessions, headers, f"{self.SITE} {year} technical sessions"))

        # Collect links to presentation pages for the given year
        pres = []
        for a in soup.select(f'a[href*="/conference/soups{year}/presentation/"]'):
            href = a.get("href") or ""
            if href:
                pres.append(urljoin(sessions, href))
        pres = sorted(set(pres))

        results: List[Dict[str, Any]] = []
        for url in tqdm(pres, f"Fetching {self.SITE} {year} papers"):
            try:
                psoup = self._soup(self._fetch_html(url, headers, "presentation page"))
                # Title
                h1 = psoup.find("h1")
                title = (h1.get_text(strip=True) if h1 else "").strip()
                if not title:
                    continue
                # Authors (from "Authors:" block)
                authors = self._parse_authors(psoup.get_text("\n", strip=True))
                # PDF
                pdf = self._pick_pdf(psoup, url)
                if not pdf:
                    # fallback: keep landing if no pdf found (rare after proceedings go live)
                    pdf = url
                results.append({"title": title, "authors": authors, "paper_url": pdf})
            except Exception:
                continue
        return results
    

# ------------------------- Public entry points -------------------------

def fetch_neurips_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return NeuripsFetcher().fetch(year)

def fetch_popets_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return PoPETsFetcher().fetch(year)

def fetch_usenix_security_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return UsenixSecurityFetcher().fetch(year)

def fetch_usenix_soups_papers(year: int) -> Dict[str, Any]:
    """Backwards-compatible function that returns make_response(...)."""
    return UsenixSoupsFetcher().fetch(year)


def fetch_papers(venue: str, year: int) -> Dict[str, Any]:
    """Generic factory-based fetch, returns make_response(...)."""
    registry = {
        "neurips": NeuripsFetcher(),
        "popets": PoPETsFetcher(),
        "usenix_security": UsenixSecurityFetcher(),
        "usenix_soup": UsenixSoupsFetcher(),
    }
    f = registry.get((venue or "").lower())
    if not f:
        return make_response("error", f"Unknown venue: {venue}. Try: {registry.keys()}", None)
    return f.fetch(year)