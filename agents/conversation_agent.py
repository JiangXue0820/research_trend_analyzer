from langchain.agents import initialize_agent, AgentType
import sys
sys.path.append("../")
from configs import config
from configs.llm_provider import get_llm
from tools.paper_fetch_tools import paper_fetch_toolkit

# Initialize the LLM (adjust parameters as needed)
config.LLM_PROVIDER='gemini'
llm = get_llm(config)

# Create the agent with the tools
paper_fetch_agent = initialize_agent(
    tools=paper_fetch_toolkit,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)