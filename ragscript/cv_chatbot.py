"""CV Search Chatbot using RAG + Semantic Search."""

from __future__ import annotations

import logging
import os
from typing import List, Tuple, Dict

from config import Settings
from pdf_loader import load_pdfs
from cv_parser import format_cv_for_display, parse_cvs_from_documents
from utils import chunk_text, setup_logging
from vector_store import EmbeddingEngine, build_vector_store, search_similar, VectorStore

logger = logging.getLogger(__name__)


def create_cv_chunks_with_source(
    documents: List[Tuple[str, str]],
    chunk_size: int = 420,
    overlap: int = 80,
) -> Tuple[List[str], Dict[int, Tuple[str, str]]]:
    """Convert CV documents into chunks with metadata mapping.
    
    Args:
        documents: List of (cv_text, source_filename) tuples
        chunk_size: Words per chunk
        overlap: Word overlap between chunks
        
    Returns:
        - List of text chunks for embedding
        - Dictionary: chunk_index -> (full_cv_text, source_filename)
    """
    
    chunks: List[str] = []
    chunk_metadata: Dict[int, Tuple[str, str]] = {}
    
    for cv_text, source_name in documents:
        cv_chunks = chunk_text(cv_text, chunk_size=chunk_size, overlap=overlap)
        
        for chunk in cv_chunks:
            chunk_idx = len(chunks)
            chunks.append(chunk)
            # Map chunk to full CV and source
            chunk_metadata[chunk_idx] = (cv_text, source_name)
        
        logger.info("Chunked CV '%s' into %d chunks", source_name, len(cv_chunks))
    
    return chunks, chunk_metadata


def search_cv_by_query(
    query: str,
    vector_store: VectorStore,
    embedder: EmbeddingEngine,
    chunk_metadata: Dict[int, Tuple[str, str]],
    top_k: int = 5,
) -> List[Tuple[str, str, float]]:
    """Search for CVs matching semantic query.
    
    Args:
        query: User's search query (e.g., "Find someone skilled in Python and AI")
        vector_store: FAISS vector store
        embedder: Embedding engine
        chunk_metadata: Mapping from chunk index to CV data
        top_k: Number of top matching chunks to retrieve
        
    Returns:
        List of (full_cv_text, source_filename, score) tuples
    """
    
    # Semantic search in vector store
    matches = search_similar(query, embedder, vector_store, top_k=top_k)
    
    if not matches:
        return []
    
    # Get full CVs from matches
    found_cvs: Dict[str, Tuple[str, float]] = {}  # source_name -> (cv_text, best_score)
    
    for chunk_text, score in matches:
        # Find which chunk index this is
        chunk_idx = vector_store.metadatas.index(chunk_text)
        
        if chunk_idx in chunk_metadata:
            cv_text, source_name = chunk_metadata[chunk_idx]
            
            # Keep the best (highest) score for each CV
            if source_name not in found_cvs or score > found_cvs[source_name][1]:
                found_cvs[source_name] = (cv_text, score)
    
    # Convert to list and sort by score (descending)
    results = [
        (cv_text, source_name, score)
        for source_name, (cv_text, score) in found_cvs.items()
    ]
    results.sort(key=lambda x: x[2], reverse=True)
    
    return results


def display_cv_results(results: List[Tuple[str, str, float]]) -> None:
    """Display CV search results nicely."""
    
    if not results:
        print("\n❌ Không tìm thấy CV phù hợp.\n")
        return
    
    print(f"\n✅ Tìm thấy {len(results)} CV phù hợp:\n")
    
    for idx, (cv_text, source_name, score) in enumerate(results, 1):
        similarity = int(score * 100)
        print(f"\n[{idx}] {source_name} (Độ tương đồng: {similarity}%)")
        print(format_cv_for_display(cv_text, source_name))


def main() -> None:
    """Main CV Chatbot loop."""
    
    setup_logging()
    
    settings = Settings.from_env()
    logger.info("Cấu hình: %s", settings.as_dict())
    
    # Initialize embedding engine
    embedder = EmbeddingEngine(settings.embedding_model)
    
    print("\n" + "="*70)
    print("🔍 CV SEARCH CHATBOT - Powered by RAG")
    print("="*70)
    print("\nTìm kiếm CV dựa trên từ ngữ tương đồng")
    print("Ví dụ: 'Tìm người biết Python', 'Có kinh nghiệm AI', etc.")
    
    # Get dataset directory
    default_dataset_dir = os.getenv("LOCAL_DATASET_DIR", "dataset")
    
    try:
        dataset_dir_input = input(f"\nNhập đường dẫn thư mục CV [{default_dataset_dir}]: ").strip()
        dataset_dir = dataset_dir_input if dataset_dir_input else default_dataset_dir
    except EOFError:
        logger.warning("Không nhận được đường dẫn. Sử dụng mặc định.")
        dataset_dir = default_dataset_dir
    
    # Load CVs
    try:
        print(f"\n⏳ Đang tải CV từ: {dataset_dir}")
        cv_documents = load_pdfs(dataset_dir)
        print(f"✅ Tải thành công {len(cv_documents)} CV")
    except Exception as exc:
        logger.error("Không thể tải CV: %s", exc)
        print(f"❌ Không thể đọc thư mục CV. Kiểm tra đường dẫn: {dataset_dir}")
        return
    
    # Prepare chunks and metadata
    print("\n⏳ Đang xử lý CV...")
    knowledge_chunks, chunk_metadata = create_cv_chunks_with_source(
        cv_documents,
        chunk_size=420,
        overlap=80,
    )
    print(f"✅ Tạo {len(knowledge_chunks)} chunks từ {len(cv_documents)} CV")
    
    # Build vector store
    print("\n⏳ Đang xây dựng vector store...")
    vector_store = build_vector_store(knowledge_chunks, embedder)
    print("✅ Vector store sẵn sàng!")
    
    print("\n" + "="*70)
    print("💡 Bạn có thể bắt đầu tìm kiếm (gõ 'thoát' hoặc 'exit' để kết thúc)")
    print("="*70)
    
    # Chat loop
    while True:
        try:
            query = input("\n🔍 Tìm kiếm: ").strip()
        except EOFError:
            print("\nTạm biệt!")
            break
        
        if not query:
            print("⚠️  Vui lòng nhập từ khóa tìm kiếm.")
            continue
        
        if query.lower() in {"exit", "quit", "bye", "thoát"}:
            print("Tạm biệt!")
            break
        
        try:
            print("\n⏳ Đang tìm kiếm...")
            results = search_cv_by_query(
                query,
                vector_store,
                embedder,
                chunk_metadata,
                top_k=10,  # Search top 10 chunks, but will return unique CVs
            )
            
            display_cv_results(results)
            
        except Exception as exc:
            logger.exception("Lỗi khi tìm kiếm: %s", exc)
            print(f"❌ Đã xảy ra lỗi: {exc}")


if __name__ == "__main__":
    main()