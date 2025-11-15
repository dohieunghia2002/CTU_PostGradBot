"""Colab-friendly RAG chatbot script."""

from __future__ import annotations

import logging
import os
from typing import List, Tuple

import google.generativeai as genai

from config import Settings
from ingestor import ingest_urls
from pdf_loader import load_pdfs
from searcher import WebSearcher
from utils import chunk_text, setup_logging
from vector_store import EmbeddingEngine, build_vector_store, search_similar

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Bạn là trợ lý AI giúp người dùng tìm kiếm thông tin dựa trên các tài liệu "
    "được cung cấp. Luôn trích dẫn nguồn ở cuối câu trả lời khi có thể."
)


def format_context(chunks: List[str]) -> str:
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(f"[Đoạn {idx}] {chunk}")
    return "\n\n".join(lines)


def build_prompt(context: str, question: str) -> str:
    return (
        "Dưới đây là các đoạn tài liệu liên quan:\n\n"
        f"{context}\n\n"
        "Trả lời câu hỏi bằng tiếng Việt, dựa trên thông tin trong các đoạn này. "
        "Nếu không tìm thấy câu trả lời, hãy nói rằng bạn không chắc chắn.\n\n"
        f"Câu hỏi: {question}"
    )


def create_chunks_with_source(
    documents: List[Tuple[str, str]],
    chunk_size: int = 420,
    overlap: int = 80,
) -> List[str]:
    """Convert documents into labeled chunks containing source information."""

    labeled_chunks: List[str] = []
    for text, source in documents:
        for chunk in chunk_text(text, chunk_size=chunk_size, overlap=overlap):
            labeled_chunks.append(f"{chunk}\n\n[Nguồn: {source}]")
    return labeled_chunks


def answer_question(
    question: str,
    vector_store,
    embedder: EmbeddingEngine,
    model: genai.GenerativeModel,
    top_k: int = 4,
) -> str:
    matches = search_similar(question, embedder, vector_store, top_k=top_k)
    if not matches:
        return "Xin lỗi, tôi chưa có đủ thông tin để trả lời câu hỏi này."

    context_chunks = [chunk for chunk, _ in matches]
    prompt = build_prompt(format_context(context_chunks), question)

    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=700),
    )

    return response.text.strip()


def main() -> None:
    setup_logging()

    settings = Settings.from_env()
    logger.info("Cấu hình: %s", settings.as_dict())

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    embedder = EmbeddingEngine(settings.embedding_model)

    print("=== RAG Chatbot ===")

    default_dataset_dir = os.getenv("LOCAL_DATASET_DIR", "dataset")
    mode_prompt = (
        "Chọn nguồn dữ liệu:\n"
        "1 - Tìm kiếm web (Tavily/SerpAPI)\n"
        f"2 - Thư mục PDF cục bộ (mặc định: {default_dataset_dir})\n"
        "Lựa chọn [2]: "
    )

    try:
        source_choice = input(mode_prompt).strip() or "2"
    except EOFError:
        logger.warning("Không nhận được lựa chọn nguồn dữ liệu. Thoát.")
        return

    knowledge_chunks: List[str] = []

    if source_choice == "1":
        try:
            searcher = WebSearcher()
        except Exception as exc:
            logger.error("Không thể khởi tạo bộ tìm kiếm web: %s", exc)
            print("Không thể khởi tạo bộ tìm kiếm web. Kiểm tra cấu hình API.")
            return

        try:
            initial_query = input(
                "Nhập từ khoá tìm kiếm tài liệu (ví dụ: 'tài liệu giáo dục trực tuyến'): "
            )
        except EOFError:
            logger.warning("Không nhận được truy vấn ban đầu. Thoát.")
            return

        results = searcher.search(initial_query, max_results=5)
        if not results:
            print("Không tìm thấy kết quả cho truy vấn.")
            return

        urls = [item.url for item in results if item.url]
        documents = ingest_urls(urls, settings.user_agent)

        if not documents:
            print("Không thể tải nội dung từ các URL.")
            return

        for doc, src in zip(documents, urls):
            for chunk in chunk_text(doc, chunk_size=420, overlap=80):
                knowledge_chunks.append(f"{chunk}\n\n[Nguồn: {src}]")

    else:
        dataset_dir = default_dataset_dir
        try:
            user_dataset = input(
                f"Nhập đường dẫn thư mục PDF [{default_dataset_dir}]: "
            ).strip()
        except EOFError:
            user_dataset = ""

        if user_dataset:
            dataset_dir = user_dataset

        try:
            pdf_documents = load_pdfs(dataset_dir)
        except Exception as exc:
            logger.error("Không thể tải PDF: %s", exc)
            print("Không thể đọc bộ tài liệu PDF. Kiểm tra đường dẫn và thử lại.")
            return

        knowledge_chunks = create_chunks_with_source(
            pdf_documents, chunk_size=420, overlap=80
        )
        print(
            f"Đã nạp {len(pdf_documents)} tài liệu PDF với tổng {len(knowledge_chunks)} đoạn."
        )

    if not knowledge_chunks:
        print("Không có dữ liệu để xây dựng kho tri thức.")
        return

    vector_store = build_vector_store(knowledge_chunks, embedder)
    print(
        "Kho tri thức đã sẵn sàng. Bạn có thể đặt câu hỏi (gõ 'thoát' để kết thúc)."
    )

    while True:
        try:
            question = input("\nBạn: ")
        except EOFError:
            print("\nTạm biệt!")
            break

        if not question.strip():
            print("Vui lòng nhập câu hỏi.")
            continue

        if question.lower() in {"exit", "quit", "bye", "thoát"}:
            print("Tạm biệt!")
            break

        try:
            answer = answer_question(question, vector_store, embedder, model)
            print(f"AI: {answer}")
        except Exception as exc:
            logger.exception("Lỗi khi trả lời: %s", exc)
            print("Đã xảy ra lỗi khi gọi mô hình. Vui lòng thử lại.")


if __name__ == "__main__":
    main()