import os
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from qdrant_client.models import Filter, FieldCondition, MatchAny
from dotenv import load_dotenv
from core.database import get_database

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")

# load models and cache them
llm_cache = None
embeddings_cache = None

def get_llm():
    global llm_cache
    if llm_cache is None:
        print("Connecting to Ollama...")
        llm_cache = OllamaLLM(
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
            readme_docs = vector_store.similarity_search(
                query="README project description overview purpose",
                k=5,
                filter=Filter(
                    should=[
                        FieldCondition(
                            key="metadata.filename",
                            match=MatchAny(any=[
                                "README.md", "README.rst", "README.txt", "readme.md",
                                "package.json", "setup.py", "pyproject.toml", "Cargo.toml"
                            ])
                        )
                    ]
                )
            )
            
            if readme_docs:
                print(f"Found {len(readme_docs)} README/metadata documents")
                return readme_docs[:k]
            else:
                print("No README found, falling back to standard search")
                
        except Exception as e:
            print(f"Priority search failed: {e}, falling back to standard search")
    
    # standard hybrid search for specific questions
    print("Using standard similarity search")
    return vector_store.similarity_search(user_query, k=k)

async def get_user_repository(user_id: str, repo_name: str = None):
    """Get user's repository from MongoDB to find collection name"""
    db = get_database()
    
    if repo_name:
        repo = await db.repositories.find_one({
            "user_id": user_id,
            "name": repo_name
        })
    else:
        repo = await db.repositories.find_one(
            {"user_id": user_id},
            sort=[("ingested_at", -1)]
        )
    
    return repo

async def save_chat_to_mongodb(user_id: str, user_message: str, ai_response: str, repo_name: str = None):
    """Save chat conversation to MongoDB"""
    try:
        db = get_database()
        chat_doc = {
            "user_id": user_id,
            "repository_name": repo_name,
            "messages": [
                {"role": "user", "content": user_message, "timestamp": datetime.utcnow()},
                {"role": "assistant", "content": ai_response, "timestamp": datetime.utcnow()}
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.chats.insert_one(chat_doc)
        print(f"Chat saved to MongoDB for user {user_id}")
    except Exception as e:
        print(f"Failed to save chat to MongoDB: {e}")

async def get_chat_response(user_query: str, user_id: str, repository_name: str = None):
    print(f"Chat service: Processing query for user {user_id}")

    repo = await get_user_repository(user_id, repository_name)
    
    if not repo:
        return "Please ingest a repository first before asking questions."
    
    collection_name = repo["collection_name"]
    print(f"Using collection: {collection_name}")

    # Use cached models
    llm = get_llm()
    embeddings = get_embeddings()
    sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            sparse_embedding=sparse_embeddings,
            collection_name=collection_name, 
            url=QDRANT_URL,
            retrieval_mode=RetrievalMode.HYBRID
        )
        print(f"Successfully connected to vector store: {collection_name}")
    except Exception as e:
        print(f"detailed error: {e}")
        raise

    # get documents with smart prioritization
    print(f"Retrieving context for: '{user_query}'")
    relevant_docs = get_prioritized_docs(vector_store, user_query, k=5)
    print(f"Retrieved {len(relevant_docs)} documents")
    if relevant_docs:
        for i, doc in enumerate(relevant_docs[:5]): 
            filename = doc.metadata.get('filename', doc.metadata.get('source', 'unknown'))
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  Doc {i+1}: {filename} - {preview}...")

    system_prompt = (
        "You are a helpful code analysis assistant. Answer the user's question based on the provided context.\n"
        "If the context contains relevant information, provide a clear and specific answer.\n"
        "If asking about what a repository is about, look for README, package.json, or setup.py content.\n"
        "Be concise but informative.\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # format docs for the prompt
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
    
    await save_chat_to_mongodb(user_id, user_query, response, repository_name)
    
    return response