import asyncio
import os
import json
from typing import Optional, List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

def save_paper_info(paper_info: Dict[str, Any], conference: str, year: int) -> str:
    filepath = os.path.join(
        "paper_list", conference.lower(), f"{conference.lower()}{year}.jsonl"
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(paper_info, ensure_ascii=False) + "\n")
    return filepath

def load_paper_list(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def paper_matches_topic(paper: Dict[str, Any], topic_keywords: List[str]) -> bool:
    title = paper.get("title")
    if not title or not title.strip():
        raise ValueError("Paper dictionary must include a non-empty 'title' field.")
    abstract = (paper.get("abstract") or "").lower()
    title = title.lower()
    keywords_lower = [kw.lower() for kw in topic_keywords]
    return any(kw in title or kw in abstract for kw in keywords_lower)

PRIVACY_TOPICS = [
    "privacy", "private", "confidential", "anonymity", "anonymization",
    "data protection", "secure", "secrecy", "obfuscation", "de-identification"
]

async def get_neurips_abstract_links(year: int) -> List[str]:
    url = f"https://papers.nips.cc/paper/{year}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a")
        paper_urls = [
            "https://papers.nips.cc" + link["href"]
            for link in links if "-Abstract.html" in link.get("href", "")
        ]
        return paper_urls

def parse_neurips_paper_from_html(url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    try:
        title = soup.find_all("h4")[0].text
        authors = soup.find_all("i")[-1].text
        abstract = soup.find_all("p")[2].text
    except Exception as e:
        raise ValueError(f"Error parsing metadata from {url}: {e}")
    info = {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "url_web": url
    }
    pdf_url = [
        tag['href'] for tag in soup.find_all('a', href=True)
        if tag['href'].lower().endswith('paper.pdf')
    ]
    if len(pdf_url) != 1:
        raise ValueError(f"Found incorrect pdf url for {url}: {pdf_url}")
    info["url_pdf"] = "https://papers.nips.cc" + pdf_url[0]
    return info

async def fetch_single_paper(url: str, keywords: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url)
            response.raise_for_status()
            meta = parse_neurips_paper_from_html(url, response.text)
            if not keywords or paper_matches_topic(meta, keywords):
                return meta
    except Exception as e:
        print(f"Error parsing {url}: {e}")
    return None

async def fetch_neurips(
    year: int,
    max_papers: Optional[int] = None,
    keywords: Optional[List[str]] = None
) -> str:
    conference = "neurips"
    paper_urls = await get_neurips_abstract_links(year)
    if max_papers:
        paper_urls = paper_urls[:max_papers]

    filepath = os.path.join("paper_list", conference.lower(), f"{conference.lower()}{year}.jsonl")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    tasks = [fetch_single_paper(url, keywords) for url in paper_urls]
    collected = []

    for coro in tqdm_asyncio.as_completed(tasks, desc=f"Parsing NeurIPS {year} abstracts", total=len(tasks)):
        meta = await coro
        if meta:
            collected.append(meta)

    # Save all results at once to minimize file I/O issues
    with open(filepath, "a", encoding="utf-8") as f:
        for meta in collected:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    return filepath


if __name__ == "__main__":
    asyncio.run(fetch_neurips(2022, max_papers=100, keywords=PRIVACY_TOPICS))