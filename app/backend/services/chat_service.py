import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from qdrant_client.models import Filter, FieldCondition, MatchAny
from dotenv import load_dotenv

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")

# load models and cache them
llm_cache = None
embeddings_cache = None

def get_llm():
    global llm_cache
    if llm_cache is None:
        print("Connecting to Ollama...")
        llm_cache = Ollama(
            model="llama3.2", 
            base_url="http://localhost:11434",
            temperature=0
        )
        print("Ollama LLM ready")
    return llm_cache

def get_embeddings():
    global embeddings_cache
    if embeddings_cache is None:
        print("loading embeddings model")
        embeddings_cache = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("embeddings cached")
    return embeddings_cache

def is_broad_question(query: str) -> bool:
    """if user req needs overview context"""
    broad_keywords = ['about', 'purpose', 'overview', 'what is', 'description', 
                      'project', 'repository', 'repo', 'summary']
    return any(keyword in query.lower() for keyword in broad_keywords)

def get_prioritized_docs(vector_store, user_query: str, k: int = 6):
    """retrieval uses hybrid mode"""
    is_broad = is_broad_question(user_query)
    
    if is_broad:
        print("Broad question detected - prioritizing README/Metadata")
        try:
            # Hybrid search with a metadata filter for READMEs
            readme_docs = vector_store.search(
                user_query,
                search_type="similarity",
                k=3,
                filter=Filter(
                    should=[
                        FieldCondition(
                            key="metadata.filename",
                            match=MatchAny(any=[
                                "README.md", "README.rst", "README.txt", "readme.md",
                                "package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "main.tf"
                            ])
                        )
                    ]
                )
            )
            print(f"Found {len(readme_docs)} prioritized documents")
            
            # get other docs via standard Hybrid search
            other_docs = vector_store.search(user_query, search_type="similarity", k=k-len(readme_docs))
            return (readme_docs + other_docs)[:k]
            
        except Exception as e:
            print(f"Priority search failed: {e}, falling back to standard hybrid")
            return vector_store.search(user_query, search_type="similarity", k=k)
    else:
        # hybrid search
        print("Specific question - using Hybrid Search (Vector + Keyword)")
        return vector_store.search(
            user_query, 
            search_type="mmr", 
            k=k,
            fetch_k=20 
        )

def get_chat_response(user_query: str):
    print(f"Chat service: Processing query for collection at {QDRANT_URL}")

    # Use cached models
    llm = get_llm()
    embeddings = get_embeddings()
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            sparse_embedding=sparse_embeddings,
            collection_name="infralens_codebase",
            url=QDRANT_URL,
            retrieval_mode=RetrievalMode.HYBRID
        )
        print("Successfully connected to vector store")
    except Exception as e:
        print(f"detailed error: {e}")
        raise

    # Get documents with smart prioritization
    print(f"Retrieving context for: '{user_query}'")
    relevant_docs = get_prioritized_docs(vector_store, user_query, k=3)
    print(f"Retrieved {len(relevant_docs)} documents")
    if relevant_docs:
        for i, doc in enumerate(relevant_docs[:3]):  # Show first 3
            filename = doc.metadata.get('filename', doc.metadata.get('source', 'unknown'))
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  Doc {i+1}: {filename} - {preview}...")

    system_prompt = (
        "You are a code analysis assistant. Answer the user's question based ONLY on the provided context.\n"
        "Be direct and specific. If the context doesn't contain the answer, say so.\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # Format docs for the prompt
    def format_docs(docs):
        formatted = []
        for d in docs:
            content = d.page_content[:600].strip()
            filename = d.metadata.get('filename', 'unknown')
            formatted.append(f"File: {filename}\n{content}")
        return "\n\n---\n\n".join(formatted)
    
    # build chain with pre-retrieved docs
    chain = (
        {"context": lambda x: format_docs(relevant_docs), "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    response = chain.invoke(user_query)
    return response