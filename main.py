# main.py
import logging
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from configs import config
from configs.logging import configure_logging
from agents.conversation_agent import master_agent

configure_logging()  # Make sure logging is set up first

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
