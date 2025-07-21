# paper_crawler.py
import os
import requests
from bs4 import BeautifulSoup
from loaders import pdf_loader
import config

def download_pdf(url, save_dir=None):
    """Download a PDF from the given URL to the specified directory (default PAPER_DIR)."""
    if save_dir is None:
        save_dir = config.PAPER_DIR
    os.makedirs(save_dir, exist_ok=True)
    local_filename = url.split('/')[-1]
    file_path = os.path.join(save_dir, local_filename)
    # Stream download to avoid loading entire file in memory
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return file_path

def crawl_conference(conf_url, conf_name, conf_year):
    """Crawl a conference webpage to retrieve papers and metadata (title, authors, abstract, PDF)."""
    resp = requests.get(conf_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    papers = []
    # Example parsing logic (selectors depend on site structure)
    for paper_item in soup.find_all('div', class_='paper-item'):
        title_tag = paper_item.find('h4', class_='title')
        title = title_tag.text.strip() if title_tag else ""
        authors_tag = paper_item.find('p', class_='authors')
        authors = authors_tag.text.strip() if authors_tag else ""
        abstract_tag = paper_item.find('div', class_='abstract')
        abstract = abstract_tag.text.strip() if abstract_tag else ""
        pdf_link_tag = paper_item.find('a', text='PDF')
        pdf_url = pdf_link_tag['href'] if pdf_link_tag else None
        pdf_path = download_pdf(pdf_url) if pdf_url else ""
        # If abstract not found on the page, attempt to extract it from the PDF
        if abstract == "" and pdf_path:
            text = pdf_loader.extract_text(pdf_path)
            abstract = pdf_loader.extract_abstract(text)
        # Prepare metadata and content for vector store
        metadata = {
            'title': title,
            'authors': authors,
            'conference': conf_name,
            'year': conf_year,
            'pdf_path': pdf_path
        }
        if abstract:
            metadata['abstract'] = abstract
        # Use title + abstract as the content for embedding
        content = title + ". " + abstract if abstract else title
        try:
            from langchain.docstore.document import Document
            doc = Document(page_content=content, metadata=metadata)
            papers.append(doc)
        except ImportError:
            papers.append({'content': content, 'metadata': metadata})
    return papers

