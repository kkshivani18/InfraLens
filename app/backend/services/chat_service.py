import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
API_KEY = os.getenv("OPENAI_API_KEY")

def get_chat_response(user_query: str):
    print(f"Chat service: Processing query for collection at {QDRANT_URL}")
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
    embeddings = OpenAIEmbeddings(openai_api_key=API_KEY, model="text-embedding-3-small")

    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            collection_name="infralens_codebase",
            url=QDRANT_URL
        )
        print("Successfully connected to vector store")
    except Exception as e:
        print(f"Failed to connect to vector store: {str(e)}")
        raise

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    system_prompt = (
        "You are a Senior DevOps Engineer and Code Expert. "
        "Use the provided context to answer the user's question. "
        "If you don't know the answer, say you don't know. "
        "Keep answers technical and concise."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    ques_ans_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, ques_ans_chain)

    response = rag_chain.invoke({"input": user_query})
    return response["answer"]