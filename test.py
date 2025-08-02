from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from configs import config
from configs.llm_provider import get_llm, get_embedding_model
import os

# 配置 LLM（Gemini or other）
config.LLM_PROVIDER = 'gemini'
llm = get_llm(config)
embedding_fn = get_embedding_model(config)

# 可以改为自己关心的论文 PDF 地址
extending_context_window_llama_3 = "https://arxiv.org/pdf/2404.19553"
attention_is_all_you_need = "https://arxiv.org/pdf/1706.03762"

# 加载文档（首次运行建议保存在本地，避免频繁下载）
if not os.path.exists("llama3.pdf"):
    import requests
    with open("llama3.pdf", "wb") as f:
        f.write(requests.get(extending_context_window_llama_3).content)
if not os.path.exists("attention.pdf"):
    import requests
    with open("attention.pdf", "wb") as f:
        f.write(requests.get(attention_is_all_you_need).content)

docs = PyMuPDFLoader("llama3.pdf").load()
docs += PyMuPDFLoader("attention.pdf").load()
print("In total {} docs".format(len(docs)))

# 切分文档为 chunk
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)
split_chunks = text_splitter.split_documents(docs)
print("In total {} split_chunks".format(len(split_chunks)))

vectorstore = FAISS.from_documents(
    documents=split_chunks,
    embedding=embedding_fn,
)
vectorstore.save_local("faiss_index")   # 持久化到本地

# Prompt 模板
PROMPT_TEMPLATE = """
Human: You are an AI assistant, and provides answers to questions by using fact based and statistical information when possible.
Use the following pieces of information to provide a concise answer to the question enclosed in <question> tags.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
<context>
{context}
</context>

<question>
{question}
</question>

The response should be specific and use statistics or numbers when possible.

Assistant:"""

prompt = PromptTemplate(
    template=PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)
retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={'k': 5, 'fetch_k': 50}
    )

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 构建 RAG Chain
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ---------------- 主程序：终端聊天 -------------------
def main():
    print("=== Paper RAG Chatbot ===")
    print("已加载论文：Llama3和Attention is All You Need")
    print("你可以直接提问，比如：What is the main contribution of the Llama3 paper?")
    print("输入 'exit' 退出。\n")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            print("Bye!")
            break
        try:
            response = rag_chain.invoke(user_input)
            print(f"Assistant: {response}\n")
        except Exception as e:
            print(f"[Error] {e}\n")

if __name__ == "__main__":
    main()
