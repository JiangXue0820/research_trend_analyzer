# conversation_agent.py
"""
This module provides the `create_research_assistant()` function, which constructs a conversational research agent using LangChain.

The agent is initialized with:
- An LLM instantiated via the `llm_provider` utility.
- Conversation memory (buffer-based) for chat history management.
- Four integrated tools:
    1. Search Papers: Queries the internal vector database of academic papers.
    2. Web Search: Performs external web searches using a search API.
    3. Load Paper: Loads and summarizes research papers from a given URL or title.
    4. Trend Analysis: Analyzes trends and generates statistics or charts from paper data.

These tools are configured with LangChain's `initialize_agent` using the Conversational ReAct agent type, allowing dynamic selection and sequencing of tool usage. The `verbose=True` option is enabled for debugging and should be disabled in production.

Returns:
    AgentExecutor: An agent instance that processes user queries in a conversational format, leveraging all defined tools.
"""

from langchain.agents import Tool, AgentType, initialize_agent
from memory.conversation_memory import ConversationMemory
from configs import llm_provider
from tools import search_tool, pdf_tool, trend_tool
from langchain.callbacks.manager import CallbackManager
from configs.llm_provider import langfuse_handler  

def create_research_assistant():
    """Create a conversational agent (ReAct) with tools for research assistance."""
    # Initialize language model and conversation memory
    llm = llm_provider.get_llm()
    memory = ConversationMemory().get_memory()
    # Define available tools for the agent
    tools = [
        Tool(name="Search Papers", func=search_tool.search_local_papers, description="Search the internal research paper database by topic or query."), 
        Tool(name="Web Search", func=search_tool.web_search, description="Search the web for information relevant to the query."), 
        Tool(name="Load Paper", func=pdf_tool.load_and_summarize_paper, description="Load a research paper PDF (by URL or title) and summarize its content."), 
        Tool(name="Trend Analysis", func=trend_tool.analyze_trends, description="Analyze research trends (topic popularity over years, top topics) based on the query.")
    ]
    # Initialize the conversational ReAct agent with tools and memory
    agent = initialize_agent(tools, llm, agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION, 
                             memory=memory, callback_magager=CallbackManager([langfuse_handler]), verbose=True)
    return agent