"""Embedding generation for medical knowledge base and RAG"""
from typing import List
import numpy as np
from openai import OpenAI
import config

# Initialize OpenAI client for embeddings
_openai_client = None


def get_openai_client():
    """Lazy load OpenAI client"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using OpenAI's text-embedding-3-small model

    This uses OpenAI's API instead of local sentence-transformers to avoid
    large PyTorch dependencies in production deployments.

    Args:
        text: Input text to embed

    Returns:
        List of floats representing the embedding vector (1536 dimensions)
    """
    client = get_openai_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (more efficient)

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors (1536 dimensions each)
    """
    client = get_openai_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]


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
