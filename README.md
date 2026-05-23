# CT DataLake - AI Semantic Search (Frappe v15 + Vue 3)

Dự án này là một hệ thống tìm kiếm ngữ nghĩa (Semantic Search) tích hợp trí tuệ nhân tạo, được xây dựng trên **Frappe Framework v15** và frontend **Vue.js 3**.

## Thành phần chính
- **Backend (Frappe v15)**: Chứa logic tìm kiếm FAISS, LLM Reranking, JD Matching và G600 Analysis dưới dạng các whitelisted API của Frappe.
- **Frontend (Vue 3 + Vite)**: Giao diện người dùng hiện đại, tốc độ cao, gọi API từ Frappe Backend.
- **AI Logic**: Sử dụng FAISS, Sentence-Transformers, và OpenAI GPT-4o.

## Cấu trúc thư mục mới
- `apps/ct_datalake/`: Chứa mã nguồn của Frappe App.
  - `ct_datalake/api.py`: Các API chính được whitelisted.
  - `ct_datalake/*.py`: Core logic (search, match, rerank).
- `frontend/`: Chứa mã nguồn frontend Vue 3.
- `Dockerfile` & `docker-compose.yml`: Cấu hình container hóa cho Frappe (Backend) và Vue (Frontend).

## Yêu cầu hệ thống
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- `OPENAI_API_KEY`

## Hướng dẫn cài đặt và chạy ứng dụng

### 1. Cấu hình biến môi trường
Export API key của OpenAI:
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 2. Khởi chạy bằng Docker Compose
```bash
docker-compose up --build
```

### 3. Truy cập ứng dụng
- **Giao diện Web (Vue 3)**: [http://localhost](http://localhost) (Port 80)
- **API Backend (Frappe)**: [http://localhost:8000/api/method/ct_datalake.api.root](http://localhost:8000/api/method/ct_datalake.api.root)

## Phát triển Frontend cục bộ
Nếu bạn muốn phát triển frontend mà không dùng Docker:
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints (Frappe)
Tất cả API được truy cập qua prefix `/api/method/ct_datalake.api.`:
- `root`: Health check
- `semantic_search`: Tìm kiếm FAISS
- `semantic_search_llm`: Tìm kiếm + Rerank LLM
- `jd_match`: Match JD văn bản
- `jd_match_upload`: Match JD từ file upload
- `g600_analyze`: Phân tích tờ trình G600 PDF

## Ghi chú
Dự án đã được cấu hình để chạy trong môi trường container với đầy đủ các dependency cho AI (FAISS, PyMuPDF, etc.) và Framework Frappe v15.

# 2. Import dữ liệu cũ vào DocType  
+ bench --site devapp.ctpai.vn execute ct_datalake.api.import_from_json

# 3. Rebuild FAISS từ DocType
+ bench --site devapp.ctpai.vn execute ct_datalake.api.rebuild_index

