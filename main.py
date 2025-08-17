# main.py
import logging
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain_experimental.plan_and_execute import (
    PlanAndExecute,
    load_agent_executor,
    load_chat_planner,
)

from tools.paper_fetch_tools import paper_fetch_toolkit
from tools.paper_summary_tools import paper_summary_toolkit
from tools.paper_rag_tools import paper_rag_toolkit

from configs import config, llm_provider, logging

logging.configure_logging()  # Make sure logging is set up first

# --- LLM Initialization ---
config.LLM_PROVIDER = "gemini"  # 按需切换
llm = llm_provider.get_llm(config)

# --- Memory Module ---
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# --- Combine tools (remove duplicate names) ---
def dedupe_tools(tools):
    seen, out = set(), []
    for t in tools:
        name = getattr(t, "name", None)
        if name and name in seen:
            continue
        if name:
            seen.add(name)
        out.append(t)
    return out

tools = dedupe_tools(
    list(paper_fetch_toolkit) +
    list(paper_summary_toolkit) +
    list(paper_rag_toolkit)
)

# --- Create Planner 与 Executor ---
planner = load_chat_planner(llm)
executor = load_agent_executor(
    llm=llm,
    tools=tools,
    verbose=True
)

# --- Build Plan-And-Execute Agent ---
master_agent = PlanAndExecute(
    planner=planner,
    executor=executor,
    memory=memory,
    verbose=True
)


if __name__ == '__main__':
    langfuse = get_client(public_key=config.LANGFUSE_API_KEY_PUBLIC)
    langfuse_handler = CallbackHandler()

    logging.info("Agent initialized. Awaiting user commands.")
    print("Agent initialized. Type a command or 'quit' to exit.")

    while True:
        user_input = input("\nYour Task: ").strip()
        if user_input.lower() in ('quit', 'exit'):
            logging.info("User requested exit. Shutting down.")
            print("Exiting.")
            break
        try:
            # master_agent.run("Please fetch the privacy-related papers from NeurIPS 2024 and generate a trend summary.")
            result = master_agent.run(user_input, callbacks=[langfuse_handler])
            logging.info(f"Agent Response: {result}")

            trace_id = getattr(langfuse_handler, "trace_id", None)
            if trace_id:
                trace_url = f"https://cloud.langfuse.com/project/{config.LANGFUSE_PROJECT_ID}/traces/{trace_id}"
                logging.info(f"Langfuse Trace: {trace_url}")

            print("\nAgent Response:", result)
        except Exception as e:
            logging.exception(f"Error during agent execution: {e}")
            print(f"Error: {e}")
