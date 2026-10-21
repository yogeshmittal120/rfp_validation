"""Shared local embedding configuration for ingestion and retrieval."""
import os

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embedding_function():
    """Return the same embedding model for both indexing and querying."""
    model_name = os.getenv("TRAINING_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    return SentenceTransformerEmbeddingFunction(model_name=model_name)
