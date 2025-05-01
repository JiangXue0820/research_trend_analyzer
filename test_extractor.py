import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import os
import re

def fetch_neurips(year, save_path=''):
    print(f"Fetching paper list for NeurIPS {year}...")
    response = requests.get(f"https://papers.nips.cc/paper/{year}")
    # Parse the response as HTML
    soup = BeautifulSoup(response.text, "html.parser")
    # Find all the <a> tags on the page (these contain the links)
    links = soup.find_all("a")
    abstract_links = []
    # Print the URLs of the links
    for link in links:
        if "-Abstract.html" in link["href"]:  # Filter the abstracts
            abstract_links.append("https://papers.nips.cc" + link["href"])
    print(f"{len(abstract_links)} abstracts found")

    def parse_paper_page(url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        print(url)
        print(BeautifulSoup)
        # The following is not a nice or robust way to filter papers and is prone to 
        # break if the website layout should change, but is sufficient for a demo
        info = {}
        info["title"] = soup.find_all("h4")[0].text
        info["authors"] = soup.find_all("i")[-1].text
        info["abstract"] = soup.find_all("p")[2].text
        info["url_web"] = url

        pdf_url = [tag['href'] for tag in soup.find_all('a', href=True) if tag['href'].lower().endswith('paper.pdf')]
        if len(pdf_url) != 1:
            raise ValueError("Found incorrect pdf url: ", pdf_url)
        else:
            info["url_pdf"] = "https://papers.nips.cc" + pdf_url[0]

        return info

    print("Extracting meta data..")
    results = {}
    for i, link in enumerate(tqdm(abstract_links[:2])):
        results[i] = parse_paper_page(link)

    if save_path == '':
        if not os.path.exists(os.path.join("paper_list", "neurips")):
            os.mkdirs(os.path.join("paper_list", "neurips"))                       
        save_path = os.path.join("paper_list", "neurips", f"neurips{year}.json")

    with open(save_path, 'w') as json_file:
        json.dump(results, json_file, indent=4)

# Execute the main function
if __name__ == "__main__":
    fetch_neurips(2019)