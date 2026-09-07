# CT DataLake - AI Semantic Search Profile

Hệ thống tìm kiếm ngữ nghĩa hồ sơ giáo sư / tiến sĩ và ghép hồ sơ với Job Description bằng AI. Có thêm chức năng phân tích tờ trình G600.

- Repo: [qh-fol-in-luv-w-data/ct-datalake-profile-search](https://github.com/qh-fol-in-luv-w-data/ct-datalake-profile-search)
- Frappe app: `ct_datalake`

## Tính năng chính

- Tìm kiếm ngữ nghĩa hồ sơ ứng viên (semantic search).
- Ghép 1 JD với danh sách hồ sơ, cho điểm phù hợp kèm giải thích.
- Phân tích tờ trình G600 dạng PDF.
- Sinh tài liệu draft từ dữ liệu ứng viên.

## Yêu cầu

- Docker + Docker Compose (production), hoặc Frappe Bench v15 + Node.js 18+ (dev).
- `OPENAI_API_KEY`.

## Chạy bằng Docker

```bash
export OPENAI_API_KEY="sk-..."
docker-compose up --build
```

- Frontend: http://localhost
- Backend: http://localhost:8000

## Cài trong Frappe Bench

```bash
cd frappe-bench
bench get-app ct_datalake https://github.com/qh-fol-in-luv-w-data/ct-datalake-profile-search
bench --site <site> install-app ct_datalake
```

Frontend dev:

```bash
cd frontend && npm install && npm run dev
```

## License

MIT © CT Group
