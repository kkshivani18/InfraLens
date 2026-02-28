import os
import shutil
import git
import re
import httpx
from datetime import datetime
from typing import Optional
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from dotenv import load_dotenv
from core.database import get_database
from core.embeddings import create_embeddings
from services.user_service import get_github_token

load_dotenv()
REPO_BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "temp_repos")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name to be Qdrant-compatible"""
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    if name and not name[0].isalpha() and name[0] != '_':
        name = '_' + name
    return name.lower()


def parse_github_repo(repo_url: str) -> Optional[tuple[str, str]]:
    """Extract owner and repo name from GitHub URL"""
    
    # handle various gitHub URL formats
    patterns = [
        r'github\.com[:/]([^/]+)/([^/\.]+)', 
    ]
    
    for pattern in patterns:
        match = re.search(pattern, repo_url)
        if match:
            return match.group(1), match.group(2)
    return None


async def check_if_repo_is_private(repo_url: str, github_token: Optional[str] = None) -> bool:
    """Check if a GitHub repo is private using GitHub API"""
    parsed = parse_github_repo(repo_url)
    if not parsed:
        print(f"Could not parse GitHub URL: {repo_url}")
        return False
    
    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                is_private = data.get("private", False)
                print(f"GitHub API check: {owner}/{repo} is {'PRIVATE' if is_private else 'PUBLIC'}")
                return is_private
            elif response.status_code == 404:
                print(f"Repository {owner}/{repo} returned 404 - might be private or inaccessible")
                return True  
            else:
                print(f"GitHub API returned {response.status_code} for {owner}/{repo}")
                return False
    except Exception as e:
        print(f"Failed to check repo privacy via API: {e}")
        return False


def get_authenticated_repo_url(repo_url: str, github_token: Optional[str] = None) -> str:
    """Convert GitHub URL to authenticated format for private repos"""
    if not github_token:
        return repo_url
    
    # handle HTTPS and SSH URLs
    if repo_url.startswith("git@github.com:"):
        repo_url = repo_url.replace("git@github.com:", "https://github.com/")
    
    # add token to HTTPS URL
    if repo_url.startswith("https://github.com/"):
        return repo_url.replace("https://github.com/", f"https://{github_token}@github.com/")
    
    return repo_url


async def ingest_repo(repo_url: str, user_id: str):
    print(f"--- Ingestion for {repo_url} started by user {user_id} ---")
    
    # get GitHub token for private repo access
    github_token = await get_github_token(user_id)
    
    if github_token:
        print(f"User has GitHub token - can access private repos")
    else:
        print(f"User has NO GitHub token - only public repos accessible")
    
    is_private = await check_if_repo_is_private(repo_url, github_token)
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    sanitized_repo_name = sanitize_collection_name(repo_name)
    collection_name = f"{user_id}_{sanitized_repo_name}"
    
    repo_path = os.path.join(REPO_BASE_PATH, f"{user_id}_{repo_name}")
    
    os.makedirs(REPO_BASE_PATH, exist_ok=True)

    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path, onerror=lambda func, path, exc: os.chmod(path, 0o777) or func(path))
        except Exception as e:
            return {"status": "error", "message": f"Failed to remove existing repo: {str(e)}"}

    print(f"Cloning repo to {repo_path}")
    try:
        authenticated_url = get_authenticated_repo_url(repo_url, github_token)
        
        if is_private:
            if not github_token:
                return {
                    "status": "error", 
                    "message": "This is a private repository. Please connect your GitHub account to access it."
                }
            print(f"Cloning PRIVATE repository with auth")
        else:
            print(f"Cloning PUBLIC repository")
        
        git.Repo.clone_from(authenticated_url, repo_path)
        print(f" Successfully cloned {'private' if is_private else 'public'} repository")
        
    except git.GitCommandError as e:
        error_msg = str(e)
        if "Authentication failed" in error_msg or "Repository not found" in error_msg:
            if is_private:
                return {
                    "status": "error", 
                    "message": "Unable to access private repository. Please ensure your GitHub account is connected and has access to this repo."
                }
            else:
                return {
                    "status": "error", 
                    "message": "Repository not found or inaccessible. Please check the URL."
                }
        return {"status": "error", "message": f"Failed to clone: {error_msg}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to clone: {str(e)}"}
    
    # load code files
    print("parsing code files")
    try:
        documents = []
        supported_extensions = {".py", ".ts", ".js", ".tsx", ".jsx", ".md", ".java", ".go", ".sh", ".rs", ".c", ".cpp", ".tf", ".yml", ".yaml", ".json", ".txt", ".html", ".css", ".sql"}
        exclude_dirs = {"node_modules", ".git", "venv", "__pycache__", "dist", "build", "target", ".next", ".vscode", ".idea"}
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # process supported extensions
                if ext in supported_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if content.strip():  
                                from langchain.schema import Document
                                doc = Document(
                                    page_content=content,
                                    metadata={"source": file_path, "filename": file}
                                )
                                documents.append(doc)
                    except Exception as e:
                        print(f"Skipping file {file}: {str(e)}")
                        continue
        
        print(f"loaded {len(documents)} files")
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse documents: {str(e)}"}

    # chunking
    print("splitting code into chunks")
    
    EXT_TO_LANG = {
        ".py": Language.PYTHON,
        ".js": Language.JS,
        ".ts": Language.JS, 
        ".tsx": Language.JS,
        ".go": Language.GO,
        ".java": Language.JAVA,
        ".rs": Language.RUST,
        ".md": Language.MARKDOWN,
        ".yaml": "yaml",
        ".yml": "yaml",  
        ".tf": "terraform"
    }

    all_texts = []
    for doc in documents:
        ext = os.path.splitext(doc.metadata.get('source', ''))[1].lower()
        lang_type = EXT_TO_LANG.get(ext)

        if isinstance(lang_type, Language):
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_type,
                chunk_size=2000,
                chunk_overlap=200
            )
        
        elif lang_type == "terraform":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                separators=["\n\nresource ", "\n\nmodule ", "\n\nvariable ", "\n\noutput ", "\n\n", "\n", " "]
            )

        elif lang_type == "yaml":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                separators=["\n---\n", "\n\n", "\n", " "]
        )
            
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000, 
                chunk_overlap=200
            )
        
        file_chunks = splitter.split_documents([doc])
        for chunk in file_chunks:
            chunk.metadata['filename'] = os.path.basename(doc.metadata.get('source', '')) 
        all_texts.extend(file_chunks)

    # embed and store
    print(f"creating embeddings")

    try:
        embeddings = create_embeddings()

        sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
        print(f"saving to qdrant")

        QdrantVectorStore.from_documents(
            all_texts,
            embeddings,
            sparse_embedding=sparse_embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=collection_name,  
            retrieval_mode=RetrievalMode.HYBRID,
            force_recreate=True  
        )
        print(f"Successfully saved to Qdrant collection: {collection_name}")
    
    except Exception as e:
        print(f"Qdrant error details: {str(e)}")
        return {"status": "error", "message": f"Failed to save to Qdrant: {str(e)}"}

    # save repo metadata to mongoDB
    try:
        db = get_database()
        repo_doc = {
            "user_id": user_id,
            "github_url": repo_url,
            "name": repo_name,
            "collection_name": collection_name,
            "is_private": is_private,
            "files_processed": len(documents),
            "chunks_stored": len(all_texts),
            "ingested_at": datetime.utcnow()
        }
        await db.repositories.insert_one(repo_doc)
        print(f" Repository metadata saved to MongoDB")
    except Exception as e:
        print(f"Failed to save to MongoDB: {e}")
    
    print(f"cloned repository data at local cleaned")
    try:
        shutil.rmtree(repo_path, onerror=lambda func, path, exc: os.chmod(path, 0o777) or func(path))
        print(f"Deleted temporary repository files")
    except Exception as e:
        print(f"Warning: Failed to delete temp repo: {e}")

    result = {
        "status": "success",
        "files_processed": len(documents),
        "chunks_stored": len(all_texts),
        "collection_name": collection_name,
        "is_private": is_private,
        "message": f"{'Private' if is_private else 'Public'} repository indexed successfully"
    }
    print(f"Ingestion completed successfully")
    print(f"Repository: {repo_name} ({'PRIVATE' if is_private else 'PUBLIC'})")
    print(f"Files: {len(documents)}, Chunks: {len(all_texts)}")
    return result