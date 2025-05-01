import asyncio
import os
import logging
from llama_index.tools.duckduckgo import DuckDuckGoSearchToolSpec
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.gemini import Gemini

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_key():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        raise ValueError("GEMINI_API_KEY environment variable not set")
    logger.info("Retrieved GEMINI_API_KEY successfully")
    return api_key

def setup_agent():
    logger.info("Setting up the agent...")
    # Configure GoogleGenAI LLM
    llm = Gemini(
        model="gemini-2.0-flash",
        temperature=0,
        api_key=get_api_key()
    )
    logger.info("Initialized GoogleGenAI LLM")

    # Initialize the DuckDuckGo search tool specification
    duckduckgo_spec = DuckDuckGoSearchToolSpec()
    tools_ddg_search = duckduckgo_spec.to_tool_list()
    logger.info(f"Initialized DuckDuckGo tools: {tools_ddg_search}")

    # Build the agent using FunctionAgent
    agent = FunctionAgent(
        llm=llm,
        tools=tools_ddg_search,
        verbose=True,
        system_prompt=(
            "Agent that leverages Google Gemini LLM and DuckDuckGo to locate the accepted papers page "
            "for a given conference and year."
        )
    )
    logger.info("FunctionAgent created successfully")
    return agent

async def find_accepted_papers(conference_name: str, year: int, agent=None):
    if agent is None:
        logger.info("No agent provided, setting up a new agent")
        agent = setup_agent()

    query = f"{conference_name} {year} accepted papers"
    logger.info(f"Executing query: {query}")
    try:
        response = await agent.run(query)
        logger.info("Query executed successfully")
        return response
    except Exception as e:
        logger.error(f"Error during query execution: {e}")
        return f"Error searching for papers: {str(e)}"

async def main():
    logger.info("Starting the agent application")
    agent = setup_agent()
    result = await find_accepted_papers("NeurIPS", 2024, agent)
    logger.info(f"Search finished")
    print("Search result:", result)

if __name__ == "__main__":
    asyncio.run(main())
