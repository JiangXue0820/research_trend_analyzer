# main.py
import logging
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner

from configs import config
from configs.llm_provider import get_llm
from configs.logging import configure_logging
from tools.paper_fetch_tools_sql import paper_fetch_toolkit
from tools.paper_analyze_tools import paper_analyze_toolkit


configure_logging()  # Make sure logging is set up first

# 1. Initialize LLM
config.LLM_PROVIDER = 'gemini'
llm = get_llm(config)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 1. Create the planner (LLM decides on multi-step plan)
planner = load_chat_planner(llm)

# 2. Create the executor (agent capable of tool execution)
executor = load_agent_executor(
    llm=llm,
    tools=paper_fetch_toolkit+paper_analyze_toolkit,
    verbose=True
)

# 3. Combine into plan-and-execute agent
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
