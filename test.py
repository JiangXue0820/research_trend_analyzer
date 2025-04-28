import requests
import json

url = "https://api.semanticscholar.org/graph/v1/paper/52adaf6d492bd9202fec4ec02de09a45b252b72a/citations"
params = {'fields': 'citingPaper.title,citingPaper.year,citingPaper.authors,citingPaper.abstract,citingPaper.citationCount', 'limit': 100, 'offset': 0}
response = requests.get(url, params=params)
papers = response.json()['data']

citations = {}
for item in papers:
    idx = len(citations)
    citing_paper = item.get("citingPaper", {})
    title = citing_paper.get("title", "")
    abstract = citing_paper.get("abstract", "")
    citation_count = citing_paper.get("citationCount", 0)
    authors_raw = citing_paper.get("authors", [])
    authors = [author.get("name", "") for author in authors_raw]
    affiliations = [author.get("affiliations", "") for author in authors_raw]  # 有些作者可能没有affiliations字段

    citations[idx] = {
        "paper_name": title,
        "authors": authors,
        "affiliations": affiliations,
        "abstract": abstract,
        "citation_count": citation_count
    }

    print(idx, citations[idx])

    with open("test.json", 'w', encoding="utf-8") as json_file:
        json.dump(citations, json_file, indent=4, ensure_ascii=False)

