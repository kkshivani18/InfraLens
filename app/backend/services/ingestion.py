import os
import shutil
import git
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
REPO_BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "temp_repos")
QDRANT_URL = os.getenv("QDRANT_URL")
API_KEY = os.getenv("OPENAI_API_KEY")


def ingest_repo(repo_url: str):
    print(f"--- Ingestion for {repo_url} started ---")
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_path = os.path.join(REPO_BASE_PATH, repo_name)
    
    os.makedirs(REPO_BASE_PATH, exist_ok=True)

    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)

    print(f"Cloning repo to {repo_path}")
    try:
        git.Repo.clone_from(repo_url, repo_path)
    except Exception as e:
        return {"status": "error", "message": f"Failed to clone: {str(e)}"}
    
    # load code files
    print("parsing code files")
    try:
        loader = GenericLoader.from_filesystem(
            repo_path,
            glob="**/*",
            suffixes=[".py", ".ts", ".js", ".tsx", ".md", ".java", ".go", ".rs", ".c", ".cpp",  ".tf", ".yml", ".yaml"],
            parser=LanguageParser()
        )
        documents = loader.load()
        print(f"loaded {len(documents)} files")
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse documents: {str(e)}"}

    # chunking
    print("splitting code into chunks")
    try:
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=2000,
            chunk_overlap=200
        )
        texts = splitter.split_documents(documents)
        print(f"created {len(texts)} chunks")
    except Exception as e:
        return {"status": "error", "message": f"Failed to split documents: {str(e)}"}

    # embed and store
    print(f"Saving to qdrant")
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=API_KEY, model="text-embedding-3-small")
        QdrantVectorStore.from_documents(
            texts,
            embeddings,
            url=QDRANT_URL,
            collection_name="infralens_codebase",
            force_recreate=True
        )
        print("Successfully saved to Qdrant")
    except Exception as e:
        print(f"Qdrant error details: {str(e)}")
        return {"status": "error", "message": f"Failed to save to Qdrant: {str(e)}"}

    result = {
        "status": "success",
        "files_processed": len(documents),
        "chunks_stored": len(texts),
        "message": "repository indexed"
    }
    print(f"Ingestion completed: {result}")
    return result