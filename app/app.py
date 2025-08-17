# app.py (Streamlit front-end)
import os
import streamlit as st
from agents.conversation_agent import create_research_assistant
from research_trend_analyzer.tools import paper_summary_tools
from tools import search_tool, trend_tool
from loaders import pdf_loader

# Page title
st.title("AI Research Assistant")

# Initialize session state for agent and data on first load
if 'agent' not in st.session_state:
    # Initialize vector store (load existing data if any)
    st.session_state.paper_store = ResearchPaperStore()
    # (Optional) We could trigger data load or crawling here if needed. 
    # For now, we assume data is already persisted or none.
    search_tool.init_paper_store(st.session_state.paper_store)
    paper_summary_tools.init_paper_store(st.session_state.paper_store)
    trend_tool.init_data([])  # If we have preloaded paper data, pass it here.
    # Create the conversational agent
    st.session_state.agent = create_research_assistant()
    st.session_state.history = []  # to store chat history for display

# File uploader for PDF analysis
uploaded_file = st.file_uploader("Upload a PDF paper for analysis", type=["pdf"])
if uploaded_file is not None:
    # Save the uploaded PDF to a temporary directory
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # Extract text from the PDF and attempt to summarize
    text = pdf_loader.extract_text(file_path)
    abstract = pdf_loader.extract_abstract(text)
    if text:
        # Summarize the uploaded paper using the PDF tool
        summary = paper_summary_tools.load_and_summarize_paper(file_path)
        st.write("**Summary of the uploaded paper:**")
        st.write(summary)
        # Add the uploaded paper to the vector store for future queries
        title = uploaded_file.name.rsplit(".", 1)[0]
        content = title + ". " + (abstract if abstract else text[:1000])
        metadata = {"title": title, "source": "user_upload"}
        if abstract:
            metadata["abstract"] = abstract
        try:
            from langchain.docstore.document import Document
            doc_to_index = Document(page_content=content, metadata=metadata)
        except ImportError:
            doc_to_index = {"page_content": content, "metadata": metadata}
        st.session_state.paper_store.index_papers([doc_to_index])
    else:
        st.error("Failed to extract text from the uploaded PDF.")

# Chat interface
st.write("## Chat with the Research Assistant")
# Display existing conversation history
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**User:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")
# Input field for new user question
user_input = st.text_input("Enter your question:", "")
if user_input:
    # Append user message to history and get assistant's response
    st.session_state.history.append({"role": "user", "content": user_input})
    response = st.session_state.agent.run(user_input)
    st.session_state.history.append({"role": "assistant", "content": response})
    # Rerun the app to display the updated conversation (Streamlit will rerun on next loop automatically)
    st.experimental_rerun()
