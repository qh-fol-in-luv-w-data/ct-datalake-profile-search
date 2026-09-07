# CT DataLake - AI Semantic Search Profile

Hệ thống tìm kiếm ngữ nghĩa (semantic search) hồ sơ giáo sư / tiến sĩ và match với Job Description, xây trên **Frappe Framework v15** (backend) + **Vue 3 + Vite** (frontend). Có thêm module phân tích tờ trình G600 (PDF).

- Repo: [qh-fol-in-luv-w-data/ct-datalake-profile-search](https://github.com/qh-fol-in-luv-w-data/ct-datalake-profile-search)
- Frappe app name: `ct_datalake`

## Thành phần chính

| Layer | Công nghệ |
|---|---|
| Backend | Frappe v15, whitelisted API dưới `ct_datalake.api.*` |
| AI | OpenAI GPT-4o (rerank + JD analyze + G600), FAISS, Sentence-Transformers (index) |
| Frontend | Vue 3 (3.5), Vite 8, axios, lucide-vue-next |
| Ingest | `pypdf`, `python-docx`, `deep-translator` |

## Cấu trúc thư mục

```
.
├── ct_datalake/                    # Frappe app
│   ├── api.py                      # Các whitelisted endpoint (search / match / analyze / draft)
│   ├── search.py                   # Core FAISS search
│   ├── llm_rerank.py               # Rerank kết quả bằng LLM
│   ├── jd_match.py                 # Match JD ↔ hồ sơ
│   ├── ai_matching.py              # Logic matching phụ trợ
│   ├── manage_index.py             # Build / rebuild FAISS index
│   ├── import_data.py              # Import dữ liệu vào DocType
│   ├── translate.py                # Dịch hỗ trợ tìm kiếm đa ngữ
│   ├── draft_doc.py                # Sinh tài liệu draft
│   ├── openai_key.py               # Đọc OPENAI_API_KEY (env / site_config)
│   ├── fastapi_app.py              # FastAPI phụ trợ (dev/test)
│   ├── hooks.py                    # SPA route /aicenter/2as-master-profile
│   ├── ct_datalake/doctype/        # DocType: candidate, dl_session, dl_action_log,
│   │                               #          dl_ai_call_log, ct_datalake_settings
│   ├── data/                       # FAISS index + metadata
│   └── www/                        # Web template gắn SPA
├── frontend/                       # Vue 3 SPA (Vite)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml                  # setuptools; extras "ml" = faiss-cpu, sentence-transformers, PyMuPDF
├── requirements.txt
└── README.md
```

## Yêu cầu hệ thống

- Docker + Docker Compose (production), hoặc Frappe Bench v15 + Node.js 18+ (dev)
- Python 3.10+
- `OPENAI_API_KEY`

## Cài đặt & chạy bằng Docker

```bash
export OPENAI_API_KEY="sk-..."
docker-compose up --build
```

- Frontend (Vue): http://localhost
- Backend (Frappe): http://localhost:8000

## Cài đặt trong Frappe Bench (dev)

```bash
cd frappe-bench
bench get-app ct_datalake https://github.com/qh-fol-in-luv-w-data/ct-datalake-profile-search
bench --site <site> install-app ct_datalake

# Thư viện AI (không đóng gói mặc định để tránh nặng bench)
./env/bin/pip install "ct_datalake[ml]"
```

Frontend dev:

```bash
cd frontend
npm install
npm run dev
```

## Whitelisted API

Base path: `/api/method/ct_datalake.api.<name>`

| Endpoint | Mô tả |
|---|---|
| `root` / `health` | Health check |
| `semantic_search` | FAISS search theo `query`, `mode`, `top_k` |
| `semantic_search_llm` | FAISS search + rerank bằng LLM |
| `jd_match` | Match JD dạng text với danh sách hồ sơ |
| `jd_match_upload` | Match JD upload từ file (PDF/DOCX) |
| `jd_analyze` | Phân tích chi tiết 1 JD |
| `jd_parse_only` | Chỉ parse JD, không match |
| `g600_analyze` | Phân tích tờ trình G600 (PDF) |
| `draft_document` | Sinh tài liệu draft |
| `get_context` | Trả context cho SPA (session, user, config) |

## Quản trị FAISS index

```bash
# Import dữ liệu cũ vào DocType
bench --site <site> execute ct_datalake.api.import_from_json

# Rebuild FAISS index từ DocType
bench --site <site> execute ct_datalake.api.rebuild_index
```

## License

MIT © CT Group
