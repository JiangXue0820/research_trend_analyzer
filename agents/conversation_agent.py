from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import ConversationBufferMemory

import sys
sys.path.append("../")
from configs import config
from configs.llm_provider import get_llm
from tools.paper_fetch_tools_sql import paper_fetch_toolkit
from tools.paper_analyze_tools import paper_analyze_toolkit

# 1. Initialize LLM
config.LLM_PROVIDER = 'gemini'
llm = get_llm(config)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 2. Create fetch and analyze agents
paper_fetch_agent = initialize_agent(
    tools=paper_fetch_toolkit,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

paper_analyze_agent = initialize_agent(
    tools=paper_analyze_toolkit,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 3. Define wrappers so each sub-agent can be used as a Tool
def run_fetch_agent(task: str):
    """Delegate the task to the paper fetch agent."""
    return paper_fetch_agent.run(task)

def run_analyze_agent(task: str):
    """Delegate the task to the paper analyze agent."""
    return paper_analyze_agent.run(task)

fetch_agent_tool = Tool(
    name="PaperFetcher",
    func=run_fetch_agent,
    description="Use this tool to fetch paper list of given conference, filter the paper by topic, load and save paper lists."
)

analyze_agent_tool = Tool(
    name="PaperAnalyzer",
    func=run_analyze_agent,
    description="Use this tool to download a certain pdf and save to vector database, answer questions about papers, and summarize highlights and research trends."
)

master_agent = initialize_agent(
    tools=[fetch_agent_tool, analyze_agent_tool],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)
