# Master Profile - AI Candidate Search (Frappe + Vue.js)

Dự án này là một ứng dụng quản lý và tìm kiếm hồ sơ ứng viên (Candidate) bằng công nghệ AI (Semantic Search với mô hình `multilingual-e5-base` và tìm kiếm ngữ nghĩa/LLM bằng GPT-4o).
Backend được xây dựng bằng Frappe Framework, lưu trữ dữ liệu dưới dạng Frappe DocType, kết hợp với FAISS để thực hiện tìm kiếm siêu tốc. Frontend sử dụng Vue.js (Vite).

## Yêu cầu Hệ Thống
- **Frappe Bench** (version 14/15)
- Python 3.11+
- Node.js (v18+)
- MariaDB & Redis (theo yêu cầu của Frappe)
- Các thư viện Python AI: `sentence-transformers`, `faiss-cpu`, `openai`, `pypdf`, `python-docx` (sẽ được tự động cài đặt qua `requirements.txt`).

---

## 1. Hướng Dẫn Cài Đặt Backend (Frappe)

### Bước 1. Lấy App về Frappe Bench
Mở Terminal, đi tới thư mục `frappe-bench` của bạn và lấy source code app về:
```bash
cd /path/to/your/frappe-bench
bench get-app https://github.com/ctg-ai-data/master-profile.git
```
*(Nếu bạn lấy code thủ công, hãy đặt thư mục này vào `frappe-bench/apps/ct_datalake`)*

### Bước 2. Cài đặt App vào Site
Cài đặt app này vào site Frappe đang hoạt động của bạn (ví dụ `mysite.local`):
```bash
bench --site mysite.local install-app ct_datalake
```

### Bước 3. Migrate Database và Tạo DocType
App đã có sẵn file script tự động khởi tạo bảng Candidate trong Database. Bạn cần chạy lệnh sau để hệ thống tự tạo cấu trúc bảng:
```bash
bench execute ct_datalake.create_doctype.create_candidate_doctype
bench --site mysite.local migrate
```

### Bước 4. Nạp Dữ Liệu Ban Đầu & Xây Dựng FAISS Index
Do dữ liệu vector khá lớn nên chúng không được đưa lên GitHub. Bạn cần chạy 2 script sau đây trong môi trường Bench để nạp dữ liệu vào DB và tự động sinh ra file `index.faiss`:

1. Đặt 2 file JSON raw (`danh_sach_giao_su_tien_si_chuyen_gia_v5.json` và `data_out_translated.json`) vào thư mục `apps/ct_datalake/ct_datalake/`. (Liên hệ team Data để lấy 2 file gốc này nếu cần nạp lại).
2. Chạy lệnh import dữ liệu vào Database:
   ```bash
   bench execute ct_datalake.import_data.run
   ```
3. Chạy lệnh Build Vector Index:
   ```bash
   bench execute ct_datalake.manage_index.run
   ```
   *(Việc này sẽ tốn khoảng 3-5 phút để tải model e5-base về và tạo vector cho hơn 7000 ứng viên).*

### Bước 5. Cấu Hình OpenAI API Key
Bạn phải tạo file `.env` tại `apps/ct_datalake/.env` với nội dung:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxx
```
Hệ thống API dùng file này để giao tiếp với GPT-4o.

---

## 2. Hướng Dẫn Cài Đặt Frontend (Vue.js)

Thư mục frontend nằm gọn trong thư mục `frontend` của app.

### Khởi động môi trường dev
Mở Terminal mới, trỏ vào thư mục frontend và chạy:
```bash
cd apps/ct_datalake/frontend
npm install
npm run dev
```
Giao diện frontend sẽ chạy tại `http://localhost:5173`. Nó sẽ gọi tự động vào Backend Frappe đang chạy ở `http://localhost:8000`.

### Build cho môi trường Production
Nếu muốn tích hợp trực tiếp Frontend vào Frappe Public:
```bash
cd apps/ct_datalake/frontend
npm install
npm run build
```

---

## 3. Các API Hỗ Trợ
App cung cấp các REST API có thể gọi dưới dạng Guest (allow_guest=True):
- `/api/method/ct_datalake.ct_datalake.api.semantic_search`
- `/api/method/ct_datalake.ct_datalake.api.semantic_search_llm`
- `/api/method/ct_datalake.ct_datalake.api.jd_match`
- `/api/method/ct_datalake.ct_datalake.api.jd_match_upload`
- `/api/method/ct_datalake.ct_datalake.api.g600_analyze`
- `/api/method/ct_datalake.ct_datalake.api.draft_document`

Chúc bạn thành công!
