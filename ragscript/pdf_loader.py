"""PDF loading utilities for local document ingestion."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from utils import clean_text

# Configure Tesseract and Poppler paths for Windows
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Try to configure Poppler path if installed manually
import os
import glob
poppler_paths = []
# Check for poppler in C:\poppler (generic and versioned)
if os.path.exists(r'C:\poppler'):
    # Try versioned path first
    versioned = glob.glob(r'C:\poppler\poppler-*\Library\bin')
    if versioned:
        poppler_paths.extend(versioned)
    # Then try generic path
    poppler_paths.append(r'C:\poppler\Library\bin')
    
poppler_paths.extend([
    r'C:\Program Files\poppler\Library\bin',
    r'C:\Program Files (x86)\poppler\Library\bin',
])

for path in poppler_paths:
    if os.path.exists(path):
        os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
        logger_msg = f"✓ Poppler configured: {path}"
        break

logger = logging.getLogger(__name__)


def _extract_text_with_ocr(pdf_path: Path, poppler_path: str = None) -> str:
    """Extract text from PDF using OCR (Tesseract) for image-based PDFs."""
    try:
        logger.info("🔍 Đang dùng OCR xử lý: %s", pdf_path.name)
        
        # Poppler path là bắt buộc cho pdf2image
        if not poppler_path:
            logger.error("✗ Poppler path không được cung cấp cho %s", pdf_path.name)
            return ""
        
        if not Path(poppler_path).exists():
            logger.error("✗ Poppler path không tồn tại: %s", poppler_path)
            return ""
        
        # Convert PDF pages to images using Poppler
        logger.debug("   Sử dụng Poppler từ: %s", poppler_path)
        images = convert_from_path(str(pdf_path), poppler_path=poppler_path, fmt="ppm")
        
        if not images:
            logger.warning("⚠ PDF không có trang hoặc không hợp lệ: %s", pdf_path.name)
            return ""
        
        ocr_text = []
        for page_num, image in enumerate(images, 1):
            try:
                page_text = pytesseract.image_to_string(image, lang="vie+eng")
                if page_text.strip():
                    ocr_text.append(page_text)
            except Exception as page_exc:
                logger.warning("⚠ Lỗi OCR trang %d của %s: %s", page_num, pdf_path.name, str(page_exc)[:60])
        
        merged = "\n".join(ocr_text)
        if merged.strip():
            logger.info("✓ OCR thành công: %s (%d trang, %d ký tự)", pdf_path.name, len(images), len(merged))
            return merged
        else:
            logger.warning("⚠ Không trích được text từ OCR: %s", pdf_path.name)
            return ""
            
    except Exception as exc:
        logger.error("✗ Lỗi OCR %s: %s", pdf_path.name, str(exc))
        logger.debug("   Chi tiết: %s", repr(exc))
        return ""


def load_pdfs(directory: str) -> List[Tuple[str, str]]:
    """Extract text content from all PDF files under a directory."""

    folder = Path(directory)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(
            f"Thư mục PDF không tồn tại hoặc không hợp lệ: {folder}"
        )

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"Không tìm thấy tệp PDF nào trong thư mục: {folder}"
        )

    documents: List[Tuple[str, str]] = []
    failed_files = []
    no_text_files = []
    ocr_files = []
    
    # Find Poppler path - bắt buộc cho OCR
    poppler_path = None
    poppler_candidates = [
        r'C:\poppler\poppler-25.07.0\Library\bin',
        r'C:\poppler\Library\bin',
        r'C:\Program Files\poppler\Library\bin',
        r'C:\Program Files (x86)\poppler\Library\bin',
    ]
    
    logger.info("🔎 Tìm kiếm Poppler...")
    for candidate in poppler_candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            # Kiểm tra file pdftoppm.exe (bắt buộc)
            if (candidate_path / "pdftoppm.exe").exists():
                poppler_path = str(candidate_path)
                logger.info("✅ Tìm thấy Poppler: %s", poppler_path)
                break
            else:
                logger.debug("   ⚠ Thư mục tồn tại nhưng thiếu pdftoppm.exe: %s", candidate)

    logger.info("Tìm thấy %d file PDF trong thư mục: %s", len(pdf_files), folder)
    if poppler_path:
        logger.info("✅ Poppler sẽ được sử dụng: %s", poppler_path)
    else:
        logger.error("❌ KHÔNG TÌM THẤY POPPLER - OCR KHÔNG HOẠT ĐỘNG!")
        logger.error("   Hãy cài đặt Poppler từ: https://github.com/oschwartz10612/poppler-windows/releases/")
    
    for pdf_path in pdf_files:
        try:
            reader = PdfReader(str(pdf_path))
            pages_text = []
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted:
                    pages_text.append(extracted)

            merged_text = clean_text("\n".join(pages_text))
            if merged_text:
                documents.append((merged_text, pdf_path.name))
                logger.info("✓ Tải thành công: %s (%d trang)", pdf_path.name, len(reader.pages))
            else:
                # PDF ảnh - thử OCR
                if poppler_path:
                    ocr_text = _extract_text_with_ocr(pdf_path, poppler_path)
                    if ocr_text:
                        cleaned_ocr = clean_text(ocr_text)
                        documents.append((cleaned_ocr, pdf_path.name))
                        ocr_files.append(pdf_path.name)
                        logger.info("📄 Tải bằng OCR: %s", pdf_path.name)
                    else:
                        no_text_files.append(pdf_path.name)
                        logger.warning(
                            "⚠ Không có văn bản: %s (%d trang - OCR thất bại)", pdf_path.name, len(reader.pages)
                        )
                else:
                    no_text_files.append(pdf_path.name)
                    logger.warning(
                        "⚠ Bỏ qua PDF ảnh (chưa tìm Poppler): %s (%d trang)", pdf_path.name, len(reader.pages)
                    )
        except Exception as exc:  # pragma: no cover - defensive logging
            failed_files.append((pdf_path.name, str(exc)[:100]))
            logger.error("✗ Lỗi khi đọc %s: %s", pdf_path.name, str(exc)[:100])

    logger.info("=" * 60)
    logger.info("Tóm tắt: ✓ %d text | 📄 %d OCR | ⚠ %d không có | ✗ %d lỗi", 
                len(documents) - len(ocr_files), len(ocr_files), len(no_text_files), len(failed_files))
    logger.info("=" * 60)
    
    if not documents:
        raise ValueError(
            "Không có nội dung hợp lệ được trích xuất từ bộ PDF."
        )

    return documents