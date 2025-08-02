# main.py
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from configs import config
from agents.conversation_agent import master_agent


if __name__ == '__main__':
    # Optionally pass credentials (or rely on env vars)
    langfuse = get_client(public_key=config.LANGFUSE_API_KEY_PUBLIC)

    # Initialize the Langfuse callback handler for LangChain
    langfuse_handler = CallbackHandler()

    print("Agent initialized. Type a command or 'quit' to exit.")
    while True:
        user_input = input("\nYour Task: ").strip()
        if user_input.lower() in ('quit', 'exit'):
            print("Exiting.")
            break
        try:
            result = master_agent.run(user_input, callbacks=[langfuse_handler])
            print("\nAgent Response:", result)
        except Exception as e:
            print(f"Error: {e}")