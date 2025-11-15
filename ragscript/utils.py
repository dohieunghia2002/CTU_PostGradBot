"""Utility helpers for text preprocessing, chunking, and logging."""

from __future__ import annotations

import logging
import re
from typing import Iterable, Iterator, List


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a simple format."""

    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(asctime)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def clean_text(text: str) -> str:
    """Normalize whitespace and strip control characters."""

    # Replace multiple whitespace characters with single space
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip()


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> List[str]:
    """Split text into overlapping chunks for embedding.

    Args:
        text: The raw text to split.
        chunk_size: Target number of words per chunk.
        overlap: Number of words to overlap between chunks to preserve context.
    """

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    step = max(1, chunk_size - overlap)

    for idx in range(0, len(words), step):
        chunk_words = words[idx : idx + chunk_size]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))

    return chunks


def batched(iterable: Iterable[str], batch_size: int) -> Iterator[list[str]]:
    """Yield successive batches from an iterable."""

    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch