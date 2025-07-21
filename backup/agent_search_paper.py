import asyncio
import os
import logging
from llama_index.tools.duckduckgo import DuckDuckGoSearchToolSpec
from llama_index.core.agent.workflow import FunctionAgent, AgentWorkflow, ReActAgent
from llama_index.llms.gemini import Gemini
from grpc.experimental import aio
aio.init_grpc_aio()

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

# Configure GoogleGenAI LLM
llm = Gemini(
    model="gemini-2.0-flash",
    temperature=0,
    api_key=get_api_key()
)
logger.info("Initialized GoogleGenAI LLM")

# Define a list of agent
logger.info("Setting up the agent...")

duckduckgo_spec = DuckDuckGoSearchToolSpec()
search_tool = duckduckgo_spec.to_tool_list()
websearch_agent = FunctionAgent(
    llm=llm,
    tools=search_tool,
    verbose=True,
    name="websearch_agent",
    description="The agent search related information on website",
    system_prompt="Agent that leverages DuckDuckGo to search related information on website."
)

resource_selection_agent = ReActAgent(
    llm=llm,
    verbose=True,
    name="resource_selection_agent",
    description="Evaluates URLs and selects the most appropriate one for information extraction.",
    system_prompt="""
You are provided with a list of URLs resulting from a web search. Your task is to evaluate these URLs and select the one that is most relevant and reliable for extracting information about accepted papers for a given conference and year. Consider factors such as domain authority, content relevance, and data completeness.
"""
)

topic_filter_agent = ReActAgent(
    llm=llm,
    verbose=True,
    name="topic_filter_agent",
    description="The agent tilter the list of papers to include only those related to the specified topic.",
    system_prompt="Filter the list of papers to include only those related to the specified topic."
)

metadata_extractor_agent = FunctionAgent(
    llm=llm,
    verbose=True,
    name="metadata_extractor_agent",
    description="The agent extract metadata of the paper (title, authors, and affiliations) and output in JSON format. ",
    system_prompt="Extract the title, authors, and affiliations from the list of papers and output in JSON format."
)


# Define a list of agent
logger.info("Setting up the agent workflow...")
workflow = AgentWorkflow(
    agents=[websearch_agent, resource_selection_agent],
    root_agent="websearch_agent",
    verbose=True
)

# Define the main asynchronous function
async def main():
    conference = "NeurIPS"
    year = 2024
    keyword = "privacy"
    save_dir = "."

    result = await workflow.run(f"Find the website page of accepted papers for {conference} {year}")
    print(result)

# Execute the main function
if __name__ == "__main__":
    asyncio.run(main())