import json
import base64
import fitz
import redis
import frappe
from openai import OpenAI
from redis.commands.search.query import Query

_rc = frappe._dict(TOP_K=5)

def get_redis_index_name():
    return "idx:candidate"

def get_openai_client() -> OpenAI:
    api_key = frappe.conf.get("openai_api_key")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=frappe.conf.get("redis_host", "localhost"),
        port=frappe.conf.get("redis_port", 6379),
        password=frappe.conf.get("redis_password", ""),
        decode_responses=True
    )

def _log_tokens(response, label=""):
    try:
        import frappe
        from ct_datalake.utils.activity_logger import ActivityLogger
        logger = ActivityLogger("DL", "ct_datalake")
        
        session_name = ""
        session_id = None
        if hasattr(frappe.local, "request") and frappe.local.request:
            session_id = frappe.request.headers.get("X-App-Session-Id") or frappe.request.headers.get("x-app-session-id")
        
        if session_id:
            session_name = frappe.db.get_value("DL Session", {"session_id": session_id}, "name")
            if not session_name:
                session_name = logger.create_session(session_id, dept="AI Matching", role="User")
        else:
            import uuid
            session_name = logger.create_session(f"fallback_{uuid.uuid4().hex[:8]}", dept="Auto", role="System")
            
        action_name = logger.start_action(session_name, action_type="ai_call", input_summary=label)
        
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "gpt-4o")
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        
        logger.log_ai_call(
            session_name=session_name,
            action_name=action_name,
            call_type=label or "ai_call",
            ai_model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success"
        )
        logger.finish_action(action_name, status="success")
    except Exception as e:
        import frappe
        frappe.logger("ct_datalake").error(f"[_log_tokens] Error: {e}")

VISION_PROMPT = '''
Đây là tờ trình kỹ thuật/hành chính. Hãy đọc TOÀN BỘ nội dung (kể cả bảng biểu).

Trả về JSON (không kèm markdown):
{
  "domains": [
    {
      "name": "tên lĩnh vực chuyên môn",
      "keywords_vi": ["từ khóa kỹ thuật tiếng Việt"],
      "keywords_en": ["specific technical keyword in English"],
      "query_vi": "chuỗi query 6-8 từ khóa kỹ thuật chuyên sâu tiếng Việt",
      "query_en": "English query string with 6-8 most specific technical keywords"
    }
  ]
}

Lưu ý:
- Liệt kê ĐẦY ĐỦ tất cả lĩnh vực trong bảng tờ trình
- Keywords phải là thuật ngữ kỹ thuật CỤ THỂ
  Ví dụ tốt: "sounding rocket propulsion trajectory simulation"
  Ví dụ xấu: "tên lửa", "rocket"
- Nếu tờ trình có nhiều trang, chỉ trả JSON một lần duy nhất ở cuối
- Không thêm text ngoài JSON
'''

JD_VISION_PROMPT = '''
Đây là văn bản mô tả công việc (Job Description) hoặc Yêu cầu tuyển dụng/chuyên gia. Hãy đọc toàn bộ nội dung (bao gồm cả bảng biểu).

Trả về JSON (không kèm markdown):
{
  "keywords": ["từ khóa 1", "từ khóa 2", "từ khóa chuyên ngành cụ thể"],
  "required_skills": ["kỹ năng 1", "kỹ năng 2"],
  "nice_to_have": ["kỹ năng ưu tiên 1"],
  "level": "fresher|mid|senior|expert",
  "domain": "lĩnh vực chuyên môn chính",
  "summary": "tóm tắt ngắn gọn yêu cầu công việc và vị trí"
}

Lưu ý:
- Keywords phải là các thuật ngữ chuyên ngành CỤ THỂ liên quan đến công việc.
- Không thêm bất kỳ text nào ngoài JSON.
'''

def _pdf_to_base64_pages(pdf_path: str, dpi: int = 150) -> list[str]:
    doc   = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        pages.append(base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return pages

def extract_keywords(pdf_path: str, gpt_client: OpenAI) -> list[dict]:
    print("\n📸 Render PDF thành ảnh...")
    pages_b64 = _pdf_to_base64_pages(pdf_path)
    print(f"  ✅ {len(pages_b64)} trang")

    content = []
    for b64 in pages_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high"
            }
        })

    content.append({"type": "text", "text": VISION_PROMPT})

    print("🤖 Gửi lên GPT-4o Vision, đang chờ phân tích...")
    resp = gpt_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": content}]
    )
    _log_tokens(resp, "extract_keywords")

    result  = json.loads(resp.choices[0].message.content)
    domains = result.get("domains", [])

    print(f"  ✅ Tìm thấy {len(domains)} lĩnh vực:\n")
    for d in domains:
        print(f"  📌 {d['name']}")
        print(f"     - VI: {', '.join(d.get('keywords_vi', []))}")
        print(f"     - EN: {', '.join(d.get('keywords_en', []))}")

    return domains

def extract_jd_requirements(pdf_path: str, gpt_client: OpenAI) -> dict:
    print("\n📸 Render JD PDF thành ảnh...")
    pages_b64 = _pdf_to_base64_pages(pdf_path)
    print(f"  ✅ {len(pages_b64)} trang")

    content = []
    for b64 in pages_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high"
            }
        })

    content.append({"type": "text", "text": JD_VISION_PROMPT})

    print("🤖 Gửi lên GPT-4o Vision để phân tích JD...")
    resp = gpt_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": content}]
    )
    _log_tokens(resp, "extract_jd_requirements")

    result = json.loads(resp.choices[0].message.content)
    print(f"  ✅ Đã trích xuất xong JD: {result.get('domain', '')}")
    return result

def search_redis(query: str, mode: str, client: redis.Redis) -> list[dict]:
    if mode not in ["in", "out"]:
        return []

    db_source = "Internal" if mode == "in" else "External"

    # Xóa ký tự đặc biệt
    safe_query = query.replace("(", "").replace(")", "").replace(":", "").replace("-", " ").strip()
    
    # Bọc query trong ngoặc kép để search nguyên cụm (Phrase Search) cho chính xác hơn.
    redis_query_str = f"(@source:{{{db_source}}}) (\"{safe_query}\")"
    q = Query(redis_query_str).paging(0, _rc.TOP_K * 4).with_scores()

    try:
        res = client.ft(get_redis_index_name()).search(q)
    except Exception as e:
        print("❌ Lỗi truy vấn RediSearch:", e)
        return []

    results = []
    seen    = set()

    for doc in res.docs:
        name_val = getattr(doc, "name", "")
        affiliation_val = getattr(doc, "affiliation", "")
        score = float(doc.score)

        candidates = frappe.get_all("Candidate", filters={"candidate_name": name_val, "source": db_source, "affiliation": affiliation_val}, fields=["*"], limit=1)
        if not candidates:
            continue
            
        candidate = candidates[0]

        if mode == "out":
            data_dict = {
                "name": candidate.candidate_name,
                "affiliation": candidate.affiliation,
                "email": candidate.email,
                "interests": candidate.interests.split(", ") if candidate.interests else [],
                "citations": candidate.citations,
                "h_index": candidate.h_index,
                "url": candidate.scholar_url,
                "city": candidate.city,
                "university_abbr": "",
                "university_name": candidate.affiliation
            }
            key = candidate.scholar_url or f"{candidate.candidate_name}|{candidate.affiliation}"
        else:
            data_dict = {
                "họ và tên": candidate.candidate_name,
                "trường": candidate.affiliation,
                "học hàm": candidate.hoc_ham,
                "học vị": candidate.hoc_vi,
                "chức vụ": candidate.chuc_vu,
                "sản phẩm thực hiện": candidate.san_pham_thuc_hien
            }
            key = f"{candidate.candidate_name}|{candidate.affiliation}"

        if key not in seen:
            seen.add(key)
            results.append({
                "score": score,
                "data": data_dict,
                "mode": mode
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)

def search_domain(domain: dict, client: redis.Redis) -> list[dict]:
    keywords = domain.get("keywords_vi", []) + domain.get("keywords_en", [])
    if not keywords:
        return []
        
    query = " | ".join(keywords)
    print(f"\n🔍 Đang tìm RediSearch: {query}")

    res_in  = search_redis(query, "in", client)
    res_out = search_redis(query, "out", client)

    return res_in + res_out
