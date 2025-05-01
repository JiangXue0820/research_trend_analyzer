import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import os
import re

def fetch_neurips(year):
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

def fetch_ccs(year):
    import requests
    from bs4 import BeautifulSoup
    import os
    import PyPDF2
    from io import BytesIO
    import re
    import time
    import argparse

    conference_support = ["ccs"]
    url = {'dblp':'https://dblp.org/db/conf/',}

    def Crawling(conference = None, year = None, save_folder = 'paper/', keywords= None):
        if conference == None:
            print('Please choose conference!')
            return
        if conference not in conference_support:
            print('Conference not support!')
            return
        if year == None:
            print('Please choose year!')
            return
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)

        dblp = url["dblp"]
        c_url = dblp + conference + '/' + conference+year +'.html'
        # https://dblp.org/db/conf/ccs/ccs2022.html

        #crawling html elements
        response = requests.get(c_url, verify=False)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # all href
        papers = soup.find_all("a",href=lambda x: x and re.search(r"doi\.org/10\.1145/\d{7}\.\d{7}", x))

        # all doi, including keynote
        pdf_links = []
        pattern = r"doi\.org/(.+)"

        for paper in papers:
            pdf_link = paper.get("href")
            match_res = 'https://dl.acm.org/doi/pdf/' + re.search(pattern, pdf_link).group(1)
            if match_res not in pdf_links:
                pdf_links.append(match_res)

        if keywords == None:
            print("No Keywords, Download All Papers")

        for pdf_link in pdf_links:
            print(pdf_link)
            pdf_response = requests.get(pdf_link)
            pdf_data = pdf_response.content
            stream = BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(stream)
            if len(pdf_reader.pages) <= 6:
                continue
            text = ""
            for i in range(3):
                page = pdf_reader.pages[i]
                text += page.extract_text()
            title = text.split("\n")[0]
            title = re.sub('[\/:*?"<>|]', '_', title)
            if keywords == None:
                match = True
            else:
                if isinstance(keywords, list):
                    for keyword in keywords:
                        match = re.search(keyword, text, flags=re.IGNORECASE)
                        if match:
                            print('Paper:', title, ". contains " + keyword)
                            break
                else:
                    match = re.search(keywords, text, flags=re.IGNORECASE)
                    if match:
                        print('Paper:', title, ". contains " + keywords)
            if match:
                filename = title + ".pdf"
                save_folder = conference+year
                if not os.path.exists(save_folder):
                    os.makedirs(save_folder)
                save_path = save_folder + "/" + filename
                with open(save_path, "wb") as f:
                    f.write(pdf_data)
            time.sleep(10)


def fetch_ieeesp(conference = None, year = None, save_folder = 'paper/', keywords= None):
    # https://github.com/lx913/Security_Papers_Crawling/blob/main/SP_Crawling.py
    if conference == None:
        print('Please choose conference!')
        return
    if conference not in conference_support:
        print('Conference not support!')
        return
    if year == None:
        print('Please choose year!')
        return
    if not os.path.exists(save_folder):
        os.mkdir(save_folder)

    dblp = url["dblp"]
    c_url = dblp + conference + '/' + conference+year +'.html'
    # https://dblp.org/db/conf/ccs/ccs2022.html

    #crawling html elements
    response = requests.get(c_url, verify=False)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # all href
    papers = soup.find_all("a",href=lambda x: x and re.compile(r'doi\.org/10\.1109/.*(\d{7})').search(x))

    # all doi, including keynote
    pdf_links = []
    pattern = r'doi\.org/10\.1109/.*(\d{7})'

    for paper in papers:
        pdf_link = paper.get("href")
        match_res = 'https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=' + re.search(pattern, pdf_link).group(1)
        if match_res not in pdf_links:
            pdf_links.append(match_res)

    if keywords == None:
        print("No Keywords, Download All Papers")

    for pdf_link in pdf_links:
        print('Latent Link: ',pdf_link)
        pdf_response = requests.get(pdf_link)
        pdf_newurl = pdf_response.content
        pdf_loc = BeautifulSoup(pdf_newurl, "html.parser")
        pdf_url = pdf_loc.find_all(src=True)
        pdf_true_link = pdf_url[-1]['src']
        print('True Link: ', pdf_true_link)
        pdf_data = requests.get(pdf_true_link).content
        stream = BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfReader(stream)
        if len(pdf_reader.pages) <= 6:
            continue
        text = ""
        for i in range(3):
            page = pdf_reader.pages[i]
            text += page.extract_text()
        title = text.split("\n")[0]
        title = re.sub('[\/:*?"<>|]', '_', title)
        if keywords == None:
            match = True
        else:
            if isinstance(keywords, list):
                for keyword in keywords:
                    match = re.search(keyword, text, flags=re.IGNORECASE)
                    if match:
                        print('Paper:', title, ". contains " + keyword)
                        break
            else:
                match = re.search(keywords, text, flags=re.IGNORECASE)
                if match:
                    print('Paper:', title, ". contains " + keywords)
        if match:
            filename = title + ".pdf"
            save_folder = conference+year
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            save_path = save_folder + "/" + filename
            with open(save_path, "wb") as f:
                f.write(pdf_data)
        time.sleep(10)


# Execute the main function
if __name__ == "__main__":
    fetch_neurips(2019)