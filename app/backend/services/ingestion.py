import os
import shutil
import git
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()
REPO_BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "temp_repos")
QDRANT_URL = os.getenv("QDRANT_URL")


def ingest_repo(repo_url: str):
    print(f"--- Ingestion for {repo_url} started ---")
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_path = os.path.join(REPO_BASE_PATH, repo_name)
    
    os.makedirs(REPO_BASE_PATH, exist_ok=True)

    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path, onerror=lambda func, path, exc: os.chmod(path, 0o777) or func(path))
        except Exception as e:
            return {"status": "error", "message": f"Failed to remove existing repo: {str(e)}"}

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
            glob="**/[!.]*",
            suffixes=[".py", ".ts", ".js", ".tsx", ".md", ".java", ".go", ".rs", ".c", ".cpp",  ".tf", ".yml", ".yaml"],
            parser=LanguageParser()
        )
        documents = loader.load()
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
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
        print(f"saving to qdrant")

        QdrantVectorStore.from_documents(
            all_texts,
            embeddings,
            sparse_embedding=sparse_embeddings,
            url=QDRANT_URL,
            collection_name="infralens_codebase",
            retrieval_mode=RetrievalMode.HYBRID,
            force_recreate=True  
        )
        print("Successfully saved to Qdrant")
    
    except Exception as e:
        print(f"Qdrant error details: {str(e)}")
        return {"status": "error", "message": f"Failed to save to Qdrant: {str(e)}"}

    result = {
        "status": "success",
        "files_processed": len(documents),
        "chunks_stored": len(all_texts),
        "message": "repository indexed"
    }
    print(f"Ingestion completed: {result}")
    return result