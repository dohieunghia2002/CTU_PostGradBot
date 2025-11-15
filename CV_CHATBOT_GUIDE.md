# 🔍 CV Search Chatbot - Hướng dẫn sử dụng

## Kiến trúc (RAG - LLM)

```
Query từ user (VD: "Tìm người biết Python")
    ↓
Embedding: Chuyển đổi thành vector
    ↓
Vector Search (FAISS): Tìm kiếm semantic trong knowledge base
    ↓
Chunk Match: Tìm chunks phù hợp
    ↓
Map to Full CV: Lấy toàn bộ CV gốc từ chunk
    ↓
Output: Hiển thị toàn bộ thông tin CV match
```

---

## 📋 Chuẩn bị

### 1. **Cài đặt Dependencies**
```bash
cd c:\chatbot\ragscript
pip install -r requirements.txt
```

**Lưu ý:** Trên Windows, cần cài đặt thêm:
- **Tesseract** (OCR): https://github.com/UB-Mannheim/tesseract/wiki
- **Poppler** (PDF processing): https://github.com/oschwartz10612/poppler-windows/releases

### 2. **Google Gemini API Key**
- Lấy từ: https://aistudio.google.com/app/apikeys
- Khi chạy chatbot, sẽ được hỏi nhập key hoặc set env var:
```powershell
$env:GOOGLE_API_KEY = "your_api_key_here"
```

### 3. **Chuẩn bị Dataset CV**
- Tạo folder `dataset` trong `c:\chatbot\ragscript\`
- Đặt các file CV PDF vào folder này
- Cấu trúc:
```
c:\chatbot\ragscript\
├── cv_chatbot.py
├── dataset/
│   ├── CV_NhanVienA.pdf
│   ├── CV_NhanVienB.pdf
│   └── ...
└── ...
```

---

## 🚀 Chạy Chatbot

### Từ Command Line:
```powershell
cd c:\chatbot\ragscript
python cv_chatbot.py
```

### Ví dụ Tương tác:

```
🔍 CV SEARCH CHATBOT - Powered by RAG
======================================================================

Tìm kiếm CV dựa trên từ ngữ tương đồng
Ví dụ: 'Tìm người biết Python', 'Có kinh nghiệm AI', etc.

Nhập đường dẫn thư mục CV [dataset]: 

⏳ Đang tải CV từ: dataset
✅ Tải thành công 45 CV
⏳ Đang xử lý CV...
✅ Tạo 2850 chunks từ 45 CV
⏳ Đang xây dựng vector store...
✅ Vector store sẵn sàng!

💡 Bạn có thể bắt đầu tìm kiếm (gõ 'thoát' hoặc 'exit' để kết thúc)

🔍 Tìm kiếm: Tìm người biết Python và Machine Learning

⏳ Đang tìm kiếm...
✅ Tìm thấy 3 CV phù hợp:

[1] CV_NhanVienA.pdf (Độ tương đồng: 95%)
======================================================================
📄 CV SOURCE: CV_NhanVienA.pdf
======================================================================

Nguyễn Văn A
Python Developer | AI Enthusiast
...
(toàn bộ nội dung CV)
======================================================================

[2] CV_NhanVienB.pdf (Độ tương đồng: 82%)
...
```

---

## 🔧 Tùy Chỉnh

### Thay đổi cấu hình embedding/model:

File `config.py`:
```python
@dataclass
class Settings:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_model: str = "gemini-2.0-flash"
```

### Thay đổi độ nhạy tìm kiếm:

File `cv_chatbot.py`, hàm `search_cv_by_query()`:
```python
top_k: int = 10,  # Tăng/giảm số chunks để search
```

Hoặc điều chỉnh chunking strategy:
```python
knowledge_chunks, chunk_metadata = create_cv_chunks_with_source(
    cv_documents,
    chunk_size=420,    # Tăng = chunk lớn hơn = kém chi tiết
    overlap=80,        # Tăng = overlap nhiều = tìm kiếm tốt hơn nhưng chậm
)
```

---

## 📊 Cách hoạt động chi tiết

### Phase 1: Loading
- Đọc tất cả PDF từ folder
- Extract text từ mỗi PDF (1 PDF = 1 CV)

### Phase 2: Chunking
- Chia mỗi CV thành chunks (420 words, overlap 80 words)
- Giữ mapping: chunk_id → full_cv_text + source_name

### Phase 3: Embedding
- Sử dụng `sentence-transformers` encode mỗi chunk
- Build FAISS index vector (in-memory)

### Phase 4: Search
- User nhập query
- Encode query → embedding
- FAISS search top-k similar chunks
- Tìm full CV của mỗi chunk
- Return unique CVs sorted by similarity score

### Phase 5: Display
- Hiển thị toàn bộ nội dung CV
- Kèm theo similarity score

---

## 🐛 Troubleshooting

| Vấn đề | Giải pháp |
|--------|----------|
| Import error `google.generativeai` | Chạy `pip install google-generativeai` |
| Error "GOOGLE_API_KEY is required" | Set env var hoặc nhập khi prompt |
| Tesseract not found | Cài từ https://github.com/UB-Mannheim/tesseract/wiki |
| Poppler not found | Cài từ https://github.com/oschwartz10612/poppler-windows/releases |
| PDF không đọc được | Kiểm tra PDF format, thử convert sang UTF-8 |
| Search kết quả chậm | Giảm `top_k`, tăng `chunk_size` |

---

## 📝 File Structure

```
c:\chatbot\
├── ragscript/
│   ├── cv_chatbot.py          ← 🔴 Main chatbot cho CV search
│   ├── cv_parser.py           ← 🔴 CV parsing + formatting
│   ├── pdf_loader.py          ← Load PDF (reuse từ dự án cũ)
│   ├── vector_store.py        ← FAISS vector store (reuse)
│   ├── config.py              ← Configuration (reuse)
│   ├── utils.py               ← Helper functions (reuse)
│   ├── requirements.txt        ← Dependencies
│   ├── dataset/               ← Folder chứa CV PDFs
│   └── __pycache__/
├── .gitignore
└── CV_CHATBOT_GUIDE.md        ← Hướng dẫn này
```

---

## ✨ Tính năng

✅ Tìm kiếm semantic (không phải keyword matching)
✅ Hỗ trợ tiếng Việt
✅ Xử lý PDF image-based (OCR)
✅ In-memory vector store (nhanh)
✅ CLI interface thân thiện
✅ Output toàn bộ thông tin CV
✅ Similarity score (%)
✅ Hỗ trợ batch search

---

## 🎯 Next Steps

1. **Chuẩn bị dataset CV** (PDF files)
2. **Cài đặt dependencies**: `pip install -r requirements.txt`
3. **Set GOOGLE_API_KEY** (cho future LLM enhancements)
4. **Chạy**: `python cv_chatbot.py`
5. **Thử tìm kiếm**: VD: "Python", "AI", "5 năm kinh nghiệm"

---

**Chúc bạn sử dụng thành công! 🚀**