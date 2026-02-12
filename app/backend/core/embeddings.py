from langchain_huggingface import HuggingFaceEmbeddings


def create_embeddings() -> HuggingFaceEmbeddings:
    """standardized embeddings instance used across the application"""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
