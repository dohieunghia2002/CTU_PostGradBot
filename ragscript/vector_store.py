"""In-memory FAISS-based vector store for retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class VectorStore:
    index: faiss.IndexFlatIP
    vectors: np.ndarray
    metadatas: List[str]


class EmbeddingEngine:
    """Wrapper around SentenceTransformer for chunk embeddings."""

    def __init__(self, model_name: str) -> None:
        logger.info("Đang tải mô hình embedding: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype("float32")


def build_vector_store(chunks: List[str], embedder: EmbeddingEngine) -> VectorStore:
    """Create a FAISS index from text chunks."""

    if not chunks:
        raise ValueError("Không có chunk nào để xây dựng vector store.")

    vectors = embedder.encode(chunks)
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    logger.info("Đã xây dựng chỉ mục FAISS với %d chunks", len(chunks))
    return VectorStore(index=index, vectors=vectors, metadatas=chunks)


def search_similar(
    query: str, embedder: EmbeddingEngine, store: VectorStore, top_k: int = 4
) -> List[Tuple[str, float]]:
    """Return the top-k most similar chunks for a query."""

    query_vector = embedder.encode([query])
    scores, indices = store.index.search(query_vector, top_k)
    matches: List[Tuple[str, float]] = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        matches.append((store.metadatas[idx], float(score)))

    return matches