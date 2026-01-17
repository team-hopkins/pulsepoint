"""Embedding generation for medical knowledge base and RAG"""
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Initialize embedding model (384 dimensions, fast and efficient)
_embedding_model = None


def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        print("📥 Loading embedding model: all-MiniLM-L6-v2...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded (384 dimensions)")
    return _embedding_model


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text

    Args:
        text: Input text to embed

    Returns:
        List of floats representing the embedding vector
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (more efficient)

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]


def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Cosine similarity score (0-1)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)

    # Cosine similarity
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    return float(similarity)
