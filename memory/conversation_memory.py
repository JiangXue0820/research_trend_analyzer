# conversation_memory.py
from langchain.memory import ConversationBufferMemory

class ConversationMemory:
    """Wrapper for conversation memory using LangChain's ConversationBufferMemory."""
    def __init__(self):
        # Initialize a conversation buffer memory to store chat history
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    def get_memory(self):
        """Return the underlying memory object (to pass into agents or chains)."""
        return self.memory
    
    def clear(self):
        """Clear the conversation memory (e.g., start a new session)."""
        self.memory.clear()
