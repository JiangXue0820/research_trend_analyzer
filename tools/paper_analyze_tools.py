import os
import requests
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.tools import StructuredTool
from langchain.agents import initialize_agent, AgentType
from pydantic import BaseModel, Field

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
class ProcessPaperArgs(BaseModel):
    pdf_path: str = Field(..., description="Path to PDF file")
    persist_directory: str = Field("./chroma_db", description="Directory for Chroma vector store")

def process_paper(pdf_path: str, persist_directory: str = "./chroma_db") -> int:
    with pdfplumber.open(pdf_path) as pdf:
        paper_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(paper_text)
    documents = [Document(page_content=chunk, metadata={"chunk_id": idx}) for idx, chunk in enumerate(chunks)]
    embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        persist_directory=persist_directory
    )
    vectorstore.persist()
    return len(chunks)

process_paper_tool = StructuredTool.from_function(
    func=process_paper,
    args_schema=ProcessPaperArgs,
    name="process_paper",
    description="Parse, chunk, embed, and save paper into Chroma vector DB."
)

# ----------- 3. Tool: RAG Q&A -----------
class RagAnswerArgs(BaseModel):
    question: str = Field(..., description="Question about the paper")
    persist_directory: str = Field("./chroma_db", description="Chroma vector DB directory")
    top_k: int = Field(5, description="Number of top chunks to retrieve")

def rag_answer(question: str, persist_directory: str = "./chroma_db", top_k: int = 5) -> str:
    embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        embedding_function=embedding_fn,
        persist_directory=persist_directory
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    docs = retriever.get_relevant_documents(question)
    context = "\n".join(doc.page_content for doc in docs)
    llm = ChatOpenAI(model="gpt-3.5-turbo")
    prompt = (
        f"Given the following paper context, answer the question as thoroughly as possible:\n\n"
        f"{context}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else response

rag_answer_tool = StructuredTool.from_function(
    func=rag_answer,
    args_schema=RagAnswerArgs,
    name="rag_answer",
    description="Answer user question about the paper using RAG (retrieval-augmented generation)."
)

# ----------- 4. Tool: Summarize Paper Insights -----------
class SummarizePaperArgs(BaseModel):
    persist_directory: str = Field("./chroma_db", description="Chroma vector DB directory")
    md_path: str = Field("paper_summary.md", description="Path to save markdown summary")

def summarize_paper_insights(persist_directory: str = "./chroma_db", md_path: str = "paper_summary.md") -> str:
    embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        embedding_function=embedding_fn,
        persist_directory=persist_directory
    )
    docs = vectorstore.similarity_search("", k=1000)
    full_text = "\n".join(doc.page_content for doc in docs)
    llm = ChatOpenAI(model="gpt-3.5-turbo")
    prompt = (
        "You are an expert research assistant. Given the full text of a scientific paper, summarize it with the following structure:\n\n"
        "1. Motivation (background)\n"
        "2. State-of-the-art methods & limitations\n"
        "3. Proposed method (main contribution, novelty, highlights)\n"
        "4. Experimental results (setup, baselines, findings)\n"
        "5. Limitations and future work\n\n"
        "Please use Markdown headings for each section.\n\n"
        f"Paper content:\n{full_text}\n\n"
        "Output the summary only, in Markdown."
    )
    response = llm.invoke(prompt)
    md_content = response.content if hasattr(response, "content") else response
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    return md_path

summarize_paper_tool = StructuredTool.from_function(
    func=summarize_paper_insights,
    args_schema=SummarizePaperArgs,
    name="summarize_paper",
    description="Summarize the paper's main insights and save to a markdown file."
)

# ----------- 5. Compose Toolkit -----------
toolkit = [
    download_paper_tool,
    process_paper_tool,
    rag_answer_tool,
    summarize_paper_tool
]

# ----------- 6. Initialize Agent -----------
if __name__ == "__main__":
    llm = ChatOpenAI(model="gpt-3.5-turbo")
    agent = initialize_agent(
        tools=toolkit,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True
    )
    print("Agent initialized. Try prompting it with tasks like:")
    print("- Download a paper from a URL.")
    print("- Process the downloaded paper and save it into a vector database.")
    print("- Answer: What is the main contribution of the paper?")
    print("- Summarize the paper and save it as a markdown file.")
