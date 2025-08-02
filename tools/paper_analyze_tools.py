import os
import requests
import sys
sys.path.append("../")
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from functools import partial
import logging

from langchain.tools import StructuredTool
from langchain.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from configs import config, llm_provider
from utils import prompts

# embedding_fn = get_embedding_model(config)


# ----------- 1. Tool: Download Paper -----------
class DownloadPaperArgs(BaseModel):
    url: str = Field(..., description="PDF URL")
    save_path: str = Field("downloaded_paper.pdf", description="Save path for PDF")

def download_paper(url: str, save_path: str = "downloaded_paper.pdf") -> str:
    r = requests.get(url)
    with open(save_path, "wb") as f:
        f.write(r.content)
    return save_path

download_paper_tool = StructuredTool.from_function(
    func=download_paper,
    args_schema=DownloadPaperArgs,
    name="download_paper",
    description="Download a research paper from a URL (PDF)."
)

# ----------- 2. Tool: Parse & Vectorize Paper -----------
class PaperInfoModel(BaseModel):
    title: str = Field(..., description="Title of the paper")
    authors: str = Field(..., description="Authors of the paper")
    venue: str = Field(..., description="Publication venue")
    year: str = Field(..., description="Publication year")
    topic: Optional[str] = Field(None, description="Topic of the paper")

class ParseAndSavePDFArgs(BaseModel):
    pdf_path: str = Field(..., description="PDF file path")
    paper_info: PaperInfoModel = Field(..., description="Dictionary containing paper metadata (title, authors, venue, url)")

def parse_and_save_pdf(
    pdf_path: str,
    paper_info: PaperInfoModel,
    embedding_fn,
    text_splitter,
    db_path
) -> dict:
    
    # load doc from pdf
    docs = PyMuPDFLoader(pdf_path).load()

    # split into chuncks
    split_chunks = text_splitter.split_documents(docs)

    # for each chunk, assign with meta data (better for retrieval w.r.t metadata)
    parsed_chunks = []
    for idx, chunk in enumerate(split_chunks):
        meta = {
            "chunk_id": idx,
            "title": paper_info.get("title", ""),
            "authors": paper_info.get("authors", ""),
            "venue": paper_info.get("venue", ""),
            "year": paper_info.get("year", ""),
            "topic": paper_info.get("topic", ""),
        }
        parsed_chunks.append(Document(page_content=chunk.page_content, metadata=meta))

    if os.path.exists(db_path):
        vectorstore = FAISS.load_local(db_path, embedding_fn)
        vectorstore.add_documents(parsed_chunks)
    else:
        vectorstore = FAISS.from_documents(parsed_chunks, embedding_fn)
    vectorstore.save_local(db_path)
    return {"chunks_added": len(parsed_chunks), "db_path": db_path}

parse_and_save_pdf_tool = StructuredTool.from_function(
    func=partial(
        parse_and_save_pdf, 
        embedding_fn=llm_provider.get_embedding_model(config), 
        text_splitter=llm_provider.get_text_splitter(config), 
        db_path=config.DB_PATH
        ),
    args_schema=ParseAndSavePDFArgs,
    name="parse_and_save_pdf",
    description="Given the directory of a PDF paper (with paper_info dict), parse the content, split into chunks, embed and save to vector database for future retrival augumented generation."
)

# ----------- 3. Tool: RAG Retriever -----------
class RagRetrieveArgs(BaseModel):
    question: str = Field(..., description="Your question about the paper")
    paper_info: PaperInfoModel = Field(..., description="Metadata about the paper for filtering")

def rag_retrieve(
    question: str,
    paper_info: PaperInfoModel,
    db_path: str,
    rag_config: Dict,
    embedding_fn,
) -> List[Document]:
    
    if not os.path.exists(db_path):
        logging.error(f"Vectorstore not found at {db_path}")
        return []
    vectorstore = FAISS.load_local(db_path, embedding_fn)

    # Construct filter dict from paper_info (exclude None or empty)
    filter_dict = paper_info.model_dump(exclude_none=True) if paper_info else {}
    # Only filter if something present
    retriever_config = rag_config.copy()
    if filter_dict:
        retriever_config = retriever_config.copy()
        retriever_config.setdefault("search_kwargs", {})
        retriever_config["search_kwargs"]["filter"] = filter_dict

    retriever = vectorstore.as_retriever(**retriever_config)
    docs = retriever.get_relevant_documents(question)
    logging.info(f"Retrieved {len(docs)} docs for question: {question} with filter: {filter_dict}")
    return docs

rag_retrieve_tool = StructuredTool.from_function(
    func=partial(
        rag_retrieve,
        db_path=config.DB_PATH,
        rag_config=config.RAG_RETRIEVER_CONFIG,
        embedding_fn=llm_provider.get_embedding_model(config),
    ),
    args_schema=RagRetrieveArgs,
    name="rag_retrieve",
    description="Retrieve relevant document chunks for a question, filtering by paper metadata (e.g. title, authors, venue, year, topic, etc.)."
)


# ----------- 3. Tool: RAG Q&A -----------
class RagQAToolArgs(BaseModel):
    question: str = Field(..., description="Question about the paper")
    context: str = Field(..., description="Relevant chunks from the retriever tool")

def rag_qa(
        question: str, 
        context: str, 
        llm) -> str:
    prompt = f"""Given the following paper context, answer the question thoroughly.

{context}

Question: {question}
Answer:"""
    try:
        response = llm.invoke(prompt)
        logging.info("[RAG] LLM generated an answer successfully.")
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logging.exception("[RAG] Exception occurred while calling LLM.")
        return f"LLM service failed: {str(e)}"

rag_qa_tool = StructuredTool.from_function(
    func=partial(rag_qa, llm=llm_provider.get_llm(config)),
    args_schema=RagQAToolArgs,
    name="rag_qa",
    description="Answer a user question about a paper given relevant context chunks."
)

# ----------- 4. Tool: Summarize Paper Insights -----------
class PaperSummaryArgs(BaseModel):
    context: str = Field(..., description="Relevant chunks from the retriever tool")

def summarize_paper(
    context: str, 
    instruction: str, 
    llm) -> str:
    
    prompt = f"""{instruction}

## Given Paper
{context}

## Summary"""
    
    try:
        response = llm.invoke(prompt)
        logging.info("[SUM] LLM generated a summary successfully.")
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logging.exception("[SUM] Exception occurred while calling LLM.")
        return f"LLM service failed: {str(e)}"

summarize_paper_tool = StructuredTool.from_function(
    func=partial(
        summarize_paper, 
        instruction=prompts.paper_summarization_template, 
        llm=llm_provider.get_llm(config)
    ),
    args_schema=PaperSummaryArgs,
    name="summarize_paper",
    description="Summarize paper content according to a specific instruction or template."
)

# # ----------- 5. Compose Toolkit -----------
# toolkit = [
#     download_paper_tool,
#     process_paper_tool,
#     rag_answer_tool,
#     summarize_paper_tool
# ]

# # ----------- 6. Initialize Agent -----------
# if __name__ == "__main__":
#     llm = ChatOpenAI(model="gpt-3.5-turbo")
#     agent = initialize_agent(
#         tools=toolkit,
#         llm=llm,
#         agent=AgentType.OPENAI_FUNCTIONS,
#         verbose=True
#     )
#     print("Agent initialized. Try prompting it with tasks like:")
#     print("- Download a paper from a URL.")
#     print("- Process the downloaded paper and save it into a vector database.")
#     print("- Answer: What is the main contribution of the paper?")
#     print("- Summarize the paper and save it as a markdown file.")
