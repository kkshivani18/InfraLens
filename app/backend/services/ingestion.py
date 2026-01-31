import os
import shutil
import git
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser

REPO_PATH = "/terraform-azure-infrastructure"

def ingest_repo(repo_url: str):
    print(f"--- Ingestion for {repo_url} started ---")

    if os.path.exists(REPO_PATH):
        shutil.rmtree(REPO_PATH)

    print(f"Cloning repo")
    try:
        git.Repo.clone_from(repo_url, REPO_PATH)
    except Exception as e:
        return {"status": "error", "message": f"Failed to clone: {str(e)}"}
    
    print("parsing code files")
    loader = GenericLoader.from_filesystem(
        REPO_PATH,
        glob="**/*",
        suffixes=[".py", ".ts", ".js", ".tsx", ".md", ".java", ".go", ".rs", ".c", ".cpp",  ".tf", ".yml", ".yaml"],
        parser=LanguageParser()
    )
    documents = loader.load()
    print(f"loaded {len(documents)} files")

    return {
        "status": "success",
        "files_processed": len(documents),
        "sample_file": documents[0].page_content[:200] if documents else "empty repo"
    }