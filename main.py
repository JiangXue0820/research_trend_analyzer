# main.py
from agents.conversation_agent import create_research_assistant
from retriever.vector_store import ResearchPaperStore
from loaders import paper_crawler
from tools import search_tool, pdf_tool, trend_tool

if __name__ == '__main__':
    # Step 1: (Optional) Crawl conference websites or load existing data
    papers = []
    # Example: Crawl a specific conference (uncomment and set actual URL and info to use)
    # papers = paper_crawler.crawl_conference("https://example.com/conf2025/papers", "ExampleConf", 2025)
    # If no crawling is done here, we assume the vector store has existing data (persisted from previous runs).
    
    # Step 2: Initialize or load the vector database
    paper_store = ResearchPaperStore()
    if papers:
        # Index newly crawled papers into the vector store
        paper_store.index_papers(papers)
    # If the persist directory already contains data, Chroma will load it on initialization above.
    
    # Step 3: Initialize tools with references to the data
    search_tool.init_paper_store(paper_store)
    pdf_tool.init_paper_store(paper_store)
    trend_tool.init_data(papers)
    
    # Step 4: Create the conversational research assistant agent
    agent = create_research_assistant()
    print("Research Assistant is ready. Type your questions (or 'exit' to quit):")
    
    # Step 5: Simple command-line chat loop
    while True:
        try:
            user_input = input("You: ")
        except EOFError:
            break
        if user_input.lower() in ("exit", "quit"):
            print("Exiting.")
            break
        # Get agent's response
        answer = agent.run(user_input)
        print(f"Assistant: {answer}")
