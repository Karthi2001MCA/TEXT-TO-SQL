"""
RAG Service — Vector-based retrieval of schema context for prompt building.
Uses FAISS for vector storage and sentence-transformers for embeddings.
"""

import os
import numpy as np
import json
from typing import List, Optional

from ..config import get_settings

settings = get_settings()

# Lazy-loaded globals
_embedder = None
_index = None
_metadata_store = []  # Parallel list of metadata for each vector


def _get_embedder():
    """Lazy-load the sentence transformer model."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


def _get_index():
    """Get or create the FAISS index."""
    global _index, _metadata_store
    if _index is None:
        import faiss
        # Try loading existing index
        index_path = os.path.join(settings.VECTOR_DB_PATH, "schema_index.faiss")
        meta_path = os.path.join(settings.VECTOR_DB_PATH, "schema_metadata.json")

        if os.path.exists(index_path) and os.path.exists(meta_path):
            _index = faiss.read_index(index_path)
            with open(meta_path, "r") as f:
                _metadata_store = json.load(f)
        else:
            # Create empty index (dimension based on model)
            embedder = _get_embedder()
            dim = embedder.get_sentence_embedding_dimension()
            _index = faiss.IndexFlatIP(dim)  # Inner product (cosine sim after normalization)
            _metadata_store = []

    return _index, _metadata_store


def _save_index():
    """Persist the FAISS index and metadata to disk."""
    import faiss
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
    index_path = os.path.join(settings.VECTOR_DB_PATH, "schema_index.faiss")
    meta_path = os.path.join(settings.VECTOR_DB_PATH, "schema_metadata.json")

    index, metadata = _get_index()
    faiss.write_index(index, index_path)
    with open(meta_path, "w") as f:
        json.dump(metadata, f)


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts into vectors."""
    embedder = _get_embedder()
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)


def add_to_index(texts: List[str], metadata_list: List[dict]):
    """
    Add texts and their metadata to the FAISS index.
    Each metadata dict should have: {id, text, table_name, column_name}
    """
    if not texts:
        return

    index, metadata_store = _get_index()
    embeddings = embed_texts(texts)

    index.add(embeddings)
    metadata_store.extend(metadata_list)
    _save_index()


def search(query: str, top_k: int = None) -> List[dict]:
    """
    Search the vector index for schema context relevant to a query.
    Returns list of {text, table_name, column_name, score}.
    """
    if top_k is None:
        top_k = settings.TOP_K_RESULTS

    index, metadata_store = _get_index()

    if index.ntotal == 0:
        return []

    # Embed the query
    query_vec = embed_texts([query])

    # Limit top_k to actual index size
    k = min(top_k, index.ntotal)

    # Search
    scores, indices = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(metadata_store):
            continue
        meta = metadata_store[idx]
        results.append({
            "text": meta.get("text", ""),
            "table_name": meta.get("table_name", ""),
            "column_name": meta.get("column_name"),
            "score": float(score),
        })

    return results


def rebuild_index(schema_texts: List[dict]):
    """
    Rebuild the entire FAISS index from scratch.
    schema_texts: list of {id, text, table_name, column_name}
    """
    global _index, _metadata_store
    import faiss

    if not schema_texts:
        return

    texts = [item["text"] for item in schema_texts]
    embeddings = embed_texts(texts)

    dim = embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(embeddings)
    _metadata_store = schema_texts

    _save_index()


def clear_index():
    """Clear the entire vector index."""
    global _index, _metadata_store
    import faiss

    embedder = _get_embedder()
    dim = embedder.get_sentence_embedding_dimension()
    _index = faiss.IndexFlatIP(dim)
    _metadata_store = []
    _save_index()


def get_index_stats() -> dict:
    """Get stats about the current index."""
    index, metadata_store = _get_index()
    return {
        "total_vectors": index.ntotal,
        "metadata_count": len(metadata_store),
        "embedding_model": settings.EMBEDDING_MODEL,
    }
