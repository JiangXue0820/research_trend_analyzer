# pdf_loader.py
from PyPDF2 import PdfReader

def extract_text(pdf_path):
    """Extract full text from a PDF file."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def extract_abstract(text):
    """Extract the abstract from the full text of a paper (if possible)."""
    if not text:
        return ""
    lower_text = text.lower()
    idx = lower_text.find("abstract")
    if idx != -1:
        # Skip the word "abstract" and any following punctuation/whitespace
        start_idx = idx + len("abstract")
        while start_idx < len(text) and text[start_idx] in [':', ' ', '\n']:
            start_idx += 1
        # Determine end of abstract: look for a blank line or an "introduction" section
        end_idx = lower_text.find("\n\n", start_idx)
        intro_idx = lower_text.find("introduction", start_idx)
        if intro_idx != -1 and (end_idx == -1 or intro_idx < end_idx):
            end_idx = intro_idx
        abstract_text = text[start_idx:end_idx].strip() if end_idx != -1 else text[start_idx:].strip()
        return abstract_text
    return ""
