import requests
import json
# from get_affiliation_from_arxiv import extract_affliation

url = "https://api.semanticscholar.org/graph/v1/paper/52adaf6d492bd9202fec4ec02de09a45b252b72a/citations"
params = {'fields': 'citingPaper.paperId,citingPaper.title,citingPaper.year,citingPaper.venue,citingPaper.authors,citingPaper.abstract,citingPaper.citationCount,citingPaper.externalIds', 'limit': 100, 'offset': 0}
response = requests.get(url, params=params).json()

if 'error' in response.keys():
    raise ValueError("Got error: ", response['error'])

papers = response['data']
citations = {}
for item in papers:
    idx = len(citations)
    citing_paper = item.get("citingPaper", {})
    paper_id = citing_paper.get("paperId", None)
    title = citing_paper.get("title", "")
    year = citing_paper.get("year", "")
    venue = citing_paper.get("venue", "")
    externalIds = citing_paper.get("externalIds", "")
    doi = externalIds.get("DOI", "")
    abstract = citing_paper.get("abstract", "")
    citation_count = citing_paper.get("citationCount", 0)
    authors_raw = citing_paper.get("authors", [])
    authors = [author.get("name", "") for author in authors_raw]
    # affiliations = extract_affliation(title)

    if doi == "":
        print("Warning: paper {} has no DOI".format(title))

    citations[idx] = {
        "paper_id": paper_id, 
        "title": title,
        "year": year, 
        "venue": venue, 
        "authors": authors,
        # "affiliations": affiliations,
        "externalIds": externalIds,
        "doi": doi,
        "abstract": abstract,
        "citation_count": citation_count
    }

    print(idx, citations[idx])

    with open("test.json", 'w', encoding="utf-8") as json_file:
        json.dump(citations, json_file, indent=4, ensure_ascii=False)

