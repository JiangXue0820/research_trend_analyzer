import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import os
import re
from typing import Optional
from pydantic import BaseModel, Field
from llama_index.tools.tool_spec.base import BaseToolSpec
from llama_index.tools.tool_spec.schema import ToolMetadata

class FetchPapersInput(BaseModel):
    year: int = Field(..., description="Year of the conference, e.g., 2023")

class FetchPapersToolSpec(BaseToolSpec):
    spec_functions = ["fetch_neurips"]

    def fetch_neurips(self, year: int) -> str:
        """
        Fetch metadata for NeurIPS papers (title, authors, abstract, URLs) from a specified year.
        """
        print(f"Fetching NeurIPS {year} paper list...")
        response = requests.get(f"https://papers.nips.cc/paper/{year}")
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a")
        abstract_links = [
            "https://papers.nips.cc" + link["href"]
            for link in links if "-Abstract.html" in link["href"]
        ]
        print(f"{len(abstract_links)} abstracts found")

        def parse_neurips_page(url):
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            info = {
                "title": soup.find_all("h4")[0].text,
                "authors": soup.find_all("i")[-1].text,
                "abstract": soup.find_all("p")[2].text,
                "url_web": url
            }
            pdf_url = [tag['href'] for tag in soup.find_all('a', href=True) if tag['href'].lower().endswith('paper.pdf')]
            if len(pdf_url) != 1:
                raise ValueError("Found incorrect pdf url: ", pdf_url)
            info["url_pdf"] = "https://papers.nips.cc" + pdf_url[0]
            return info

        results = {i: parse_neurips_page(link) for i, link in enumerate(tqdm(abstract_links[:2]))}  # For demo

        default_path = os.path.join("paper_list", "neurips", f"neurips{year}.json")
        os.makedirs(os.path.dirname(default_path), exist_ok=True)

        with open(default_path, 'w') as f:
            json.dump(results, f, indent=4)

        return f"Saved NeurIPS {year} paper metadata to {default_path}"
    
    

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="fetch_papers_tool",
            description="Fetch paper metadata (title, authors, abstract, URLs) from major ML conferences. Supports NeurIPS.",
            input_schema=FetchPapersInput
        )