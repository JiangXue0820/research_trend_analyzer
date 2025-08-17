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
# from tools.paper_rag_tools import paper_rag_toolkit

from configs import config, llm_provider, log_config

# Configure logging first
log_config.configure_logging()
logging.info("Starting up...")

def dedupe_tools(tools):
    """Remove duplicate tools by name (preserve first occurrence)."""
    seen, out = set(), []
    for t in tools:
        name = getattr(t, "name", None)
        if name and name in seen:
            continue
        if name:
            seen.add(name)
        out.append(t)
    return out

def build_agent():
    logging.info("Booting agent...")

    # LLM
    config.LLM_PROVIDER = "gemini"  # adjust if needed
    llm = llm_provider.get_llm(config)
    logging.info("LLM initialized with provider=%s", config.LLM_PROVIDER)

    # Memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )
    logging.info("Conversation memory ready (key=%s)", "chat_history")

    # Tools
    tools = dedupe_tools(
        list(paper_fetch_toolkit)
        + list(paper_summary_toolkit)
        # + list(paper_rag_toolkit)
    )
    logging.info("Loaded %d tools: %s", len(tools), [getattr(t, "name", "unnamed") for t in tools])

    # Planner & Executor
    planner = load_chat_planner(llm)
    executor = load_agent_executor(
        llm=llm,
        tools=tools,
        verbose=True,
    )
    logging.info("Planner and executor constructed.")

    # Plan-and-Execute agent
    master_agent = PlanAndExecute(
        planner=planner,
        executor=executor,
        memory=memory,
        verbose=True,
    )
    logging.info("Plan-and-Execute agent is ready.")
    return master_agent

if __name__ == '__main__':
    # Langfuse (optional; safe init)
    try:
        langfuse_client = get_client(  # don't shadow module name
            public_key=getattr(config, "LANGFUSE_API_KEY_PUBLIC", None)
            # secret key / host can also be set via env; add here if you keep them in config:
            # , secret_key=config.LANGFUSE_API_KEY_SECRET,
            # , host=config.LANGFUSE_HOST,
        )
        langfuse_handler = CallbackHandler()
        logging.info("Langfuse client and callback handler initialized.")
    except Exception as e:
        langfuse_client = None
        langfuse_handler = None
        logging.warning("Langfuse init skipped/failed: %s", e)

    master_agent = build_agent()
    logging.info("Agent initialized. Awaiting user commands.")
    print("Agent initialized. Type a command or 'quit' to exit.")

    while True:
        user_input = input("\nYour Task: ").strip()
        if user_input.lower() in ('quit', 'exit'):
            logging.info("User requested exit. Shutting down.")
            print("Exiting.")
            break
        try:
            callbacks = [langfuse_handler] if langfuse_handler else None
            result = master_agent.run(user_input, callbacks=callbacks)
            logging.info("Agent Response: %s", result)

            # Emit Langfuse trace URL if available
            if langfuse_handler:
                trace_id = getattr(langfuse_handler, "trace_id", None)
                if trace_id and getattr(config, "LANGFUSE_PROJECT_ID", None):
                    trace_url = f"https://cloud.langfuse.com/project/{config.LANGFUSE_PROJECT_ID}/traces/{trace_id}"
                    logging.info("Langfuse Trace: %s", trace_url)

            print("\nAgent Response:", result)
        except Exception as e:
            logging.exception("Error during agent execution: %s", e)
            print(f"Error: {e}")
