import argparse
import requests
import json
import pandas as pd
from tqdm import tqdm

# --- 查询主论文，获取paperId ---
def get_paper_id(paper_title: str) -> str:
    url = f"https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": paper_title,
        "fields": "title",
        "limit": 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    if not data["data"]:
        raise Exception(f"没有找到标题为 '{paper_title}' 的论文！")
    return data["data"][0]["paperId"]

# --- 查询引用这篇paper的论文，自动分页 ---
def fetch_citations(paper_id: str, max_papers: int = 100):
    citations = []
    page = 0
    per_page = 100  # Semantic Scholar每页最大100条
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"

    pbar = tqdm(total=max_papers, desc="抓取引用论文")
    while len(citations) < max_papers:
        offset = page * per_page
        response = requests.get(url)
        data = response.json()
        batch = data.get("data", [])
        print("data", data)
        print("batch", batch)
        if not batch:
            print("[Info] 没有更多引用了。")
            break

        for item in batch:
        # for item in data['data']:
            citing_paper = item.get("citingPaper", {})
            title = citing_paper.get("title", "")
            abstract = citing_paper.get("abstract", "")
            citation_count = citing_paper.get("citationCount", 0)
            authors_raw = citing_paper.get("authors", [])
            authors = [author.get("name", "") for author in authors_raw]
            affiliations = [author.get("affiliations", "") for author in authors_raw]  # 有些作者可能没有affiliations字段

            citations.append({
                "paper_name": title,
                "authors": authors,
                "affiliations": affiliations,
                "abstract": abstract,
                "citation_count": citation_count
            })

            pbar.update(1)
            if len(citations) >= max_papers:
                break

        page += 1  # 翻到下一页

    pbar.close()
    return citations

# --- 主程序 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用Semantic Scholar API抓取被引用论文")
    parser.add_argument("--paper_id", type=str, required=True, help="要查询的论文标题")
    parser.add_argument("--max_papers", type=int, default=500, help="最大抓取引用论文数量")
    args = parser.parse_args()

    paper_title = args.paper_id
    max_papers = args.max_papers

    print(f"[Info] 正在检索主论文: {paper_title}")
    paper_id = get_paper_id(paper_title)
    print(f"[Info] 找到Paper ID: {paper_id}")

    citations = fetch_citations(paper_id, max_papers)

    # 保存成 JSON
    output_json_file = "citations_from_semanticscholar.json"
    with open(output_json_file, "w", encoding="utf-8") as f:
        json.dump(citations, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 抓取完成，结果已保存到 {output_json_file}")

    # 保存成 Excel
    output_excel_file = "citations_from_semanticscholar.xlsx"
    df = pd.DataFrame(citations)
    df.to_excel(output_excel_file, index=False)

    print(f"✅ 同时保存成Excel文件: {output_excel_file}")
