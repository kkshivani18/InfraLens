import os
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_qdrant import QdrantVectorStore
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from dotenv import load_dotenv
import torch

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")

def get_chat_response(user_query: str):
    print(f"Chat service: Processing query for collection at {QDRANT_URL}")
    
    # init local LLM 
    print("Loading local LLM...")
    model_id = "google/flan-t5-base"  
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    
    pipe = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        max_length=512,
        do_sample=False,
        device=-1  # Use CPU
    )
    
    llm = HuggingFacePipeline(pipeline=pipe)
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

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