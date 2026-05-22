import frappe
import os
import json
import uuid
import tempfile
from typing import Literal, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Load .env từ thư mục gốc của app (ct_datalake/)
_env_path = Path(__file__).resolve().parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# ─── internal modules ───────────────────────────────────────────────
from .search import search as faiss_search
from .llm_rerank import rerank
from .jd_match import (
    match_jd,
    normalize_candidate,
    parse_jd,
    extract_text_from_upload as _extract_text,
)
from .ai_matching import extract_keywords, load_datasets, search_domain
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from . import ai_matching as _rc

# ─── OpenAI client ──────────────────────────────────────────────────
_api_key = os.getenv("OPENAI_API_KEY", "").strip()
gpt_client = OpenAI(api_key=_api_key) if _api_key else None

# ─── Lazy-load heavy resources once ─────────────────────────────────
_embed_model: Optional[SentenceTransformer] = None
_datasets: Optional[dict] = None

def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
    return _embed_model

def get_datasets() -> dict:
    global _datasets
    if _datasets is None:
        _datasets = load_datasets()
    return _datasets

# ════════════════════════════════════════════════════════════════════
# ROUTES (Frappe Whitelisted)
# ════════════════════════════════════════════════════════════════════

# ── Health check ────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def root():
    """Kiểm tra trạng thái API"""
    return {
        "status": "ok",
        "service": "AI Candidate Search API (Frappe)",
        "version": "1.0.0",
        "endpoints": [
            "/api/method/ct_datalake.ct_datalake.api.root",
            "/api/method/ct_datalake.ct_datalake.api.health",
            "/api/method/ct_datalake.ct_datalake.api.semantic_search",
            "/api/method/ct_datalake.ct_datalake.api.semantic_search_llm",
            "/api/method/ct_datalake.ct_datalake.api.jd_match",
            "/api/method/ct_datalake.ct_datalake.api.jd_match_upload",
            "/api/method/ct_datalake.ct_datalake.api.g600_analyze",
        ],
    }

@frappe.whitelist(allow_guest=True)
def health():
    """Health check chi tiết"""
    return {
        "status": "healthy",
        "openai_configured": bool(_api_key),
        "embed_model_loaded": _embed_model is not None,
        "datasets_loaded": _datasets is not None,
    }

# ── Semantic Search (FAISS) ─────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def semantic_search(query: str, mode: str = "in", top_k: int = 5):
    """
    Tìm kiếm ứng viên sử dụng FAISS semantic search.
    """
    try:
        top_k = int(top_k)
        raw = faiss_search(query=query, mode=mode, top_k=top_k)
    except Exception as e:
        frappe.throw(f"Search error: {str(e)}")

    results = []
    for r in raw:
        norm = normalize_candidate(r["data"], mode)
        results.append({
            "faiss_score": round(r["score"], 4),
            "candidate": norm,
            "raw": r["data"],
        })

    return {
        "query": query,
        "mode": mode,
        "total": len(results),
        "results": results,
    }

# ── Semantic Search (LLM Rerank) ────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def semantic_search_llm(query: str, mode: str = "in", top_k: int = 5):
    """
    Tìm kiếm FAISS rồi đưa kết quả vào LLM để phân tích.
    """
    if not gpt_client:
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    try:
        top_k = int(top_k)
        raw = faiss_search(
            query=query,
            mode=mode,
            top_k=max(top_k * 2, 10)
        )
    except Exception as e:
        frappe.throw(f"Search error: {str(e)}")

    if not raw:
        return {"query": query, "mode": mode, "total_found": 0, "llm_analysis": ""}

    try:
        analysis = rerank(query=query, candidates=raw[:top_k], mode=mode)
    except Exception as e:
        frappe.throw(f"LLM rerank error: {str(e)}")

    return {
        "query": query,
        "mode": mode,
        "total_found": len(raw),
        "candidates_sent_to_llm": top_k,
        "llm_analysis": analysis,
    }

# ── JD Matching (via form fields) ───────────────────────────────────
@frappe.whitelist(allow_guest=True)
def jd_match(jd_text: str, mode: str = "in", top_k: int = 5, fast: bool = False):
    """
    Match JD với ứng viên.
    """
    if not gpt_client and not frappe.parse_json(fast):
        frappe.throw("OPENAI_API_KEY chưa cấu hình. Dùng fast=true để chỉ dùng FAISS.")

    try:
        top_k = int(top_k)
        fast = frappe.parse_json(fast)
        result = match_jd(
            jd_text=jd_text,
            mode=mode,
            top_k=top_k,
            fast=fast,
        )
    except Exception as e:
        frappe.throw(f"JD match error: {str(e)}")

    return {
        "parsed_jd": result.get("parsed_jd", {}),
        "total_found": result.get("total_found", 0),
        "candidates": result.get("candidates", []),
    }

# ── JD Matching (File Upload) ───────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def jd_match_upload():
    """
    Upload file JD → extract text → match ứng viên.
    Sử dụng frappe.request.files
    """
    if not frappe.request.files:
        frappe.throw("Chưa có file nào được upload")

    file = frappe.request.files.get("file")
    if not file:
        frappe.throw("Vui lòng upload file với key 'file'")

    mode = frappe.form_dict.get("mode", "in")
    top_k = int(frappe.form_dict.get("top_k", 5))
    fast = frappe.parse_json(frappe.form_dict.get("fast", "false"))

    allowed = (".txt", ".md", ".pdf", ".docx")
    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in allowed):
        frappe.throw(f"Định dạng không hỗ trợ. Chỉ chấp nhận: {', '.join(allowed)}")

    # Tạo mock object để tái dùng hàm extract_text_from_upload
    class _MockUpload:
        def __init__(self, name, data):
            self.name = name
            self._data = data
        def read(self):
            return self._data

    try:
        jd_text = _extract_text(_MockUpload(file.filename, file.stream.read()))
    except Exception as e:
        frappe.throw(str(e))

    try:
        result = match_jd(
            jd_text=jd_text,
            mode=mode,
            top_k=top_k,
            fast=fast,
        )
    except Exception as e:
        frappe.throw(f"JD match error: {str(e)}")

    return {
        "parsed_jd": result.get("parsed_jd", {}),
        "total_found": result.get("total_found", 0),
        "candidates": result.get("candidates", []),
    }

# ── G600 PDF Analysis ────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def g600_analyze():
    """
    Upload PDF tờ trình G600 → GPT-4o Vision đọc và trích xuất lĩnh vực.
    """
    if not gpt_client:
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    if not frappe.request.files:
        frappe.throw("Chưa có file nào được upload")

    file = frappe.request.files.get("file")
    if not file:
        frappe.throw("Vui lòng upload file với key 'file'")

    source = frappe.form_dict.get("source", "both")
    top_k = int(frappe.form_dict.get("top_k", 5))
    score_threshold = float(frappe.form_dict.get("score_threshold", 0.40))

    if not (file.filename or "").lower().endswith(".pdf"):
        frappe.throw("Chỉ chấp nhận file PDF")

    file_bytes = file.stream.read()

    # Ghi PDF tạm thời
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        domains = extract_keywords(tmp_path, gpt_client)
    except Exception as e:
        frappe.throw(f"GPT Vision error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not domains:
        frappe.throw("GPT không trích xuất được lĩnh vực nào từ PDF")

    datasets = get_datasets()
    embed_model = get_embed_model()

    if source == "in":
        active = {k: v for k, v in datasets.items() if k == "in"}
    elif source == "out":
        active = {k: v for k, v in datasets.items() if k == "out"}
    else:
        active = datasets

    if not active:
        frappe.throw("Không tìm thấy FAISS index. Kiểm tra file index.faiss / index_out.faiss")

    _rc.TOP_K = top_k
    _rc.SCORE_THRESHOLD = score_threshold

    domain_results = []
    for domain in domains:
        hits = search_domain(domain, active, embed_model)
        candidates = []
        for hit in hits:
            d = hit["data"]
            mode = hit["mode"]
            norm = normalize_candidate(d, mode)
            candidates.append({
                "source": "🌐 Google Scholar" if mode == "out" else "🏫 Nội bộ",
                "faiss_score": hit["score"],
                "candidate": norm,
                "raw": d,
            })

        domain_results.append({
            "domain_name": domain["name"],
            "query_vi": domain.get("query_vi", ""),
            "query_en": domain.get("query_en", ""),
            "keywords_vi": domain.get("keywords_vi", []),
            "keywords_en": domain.get("keywords_en", []),
            "total_candidates": len(candidates),
            "candidates": candidates,
        })

    return {
        "source": source,
        "top_k_per_domain": top_k,
        "score_threshold": score_threshold,
        "total_domains": len(domain_results),
        "domains": domain_results,
    }

# ── Parse JD only ────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def jd_parse_only(query: str):
    """
    Gửi JD text → GPT phân tích.
    """
    if not gpt_client:
        frappe.throw("OPENAI_API_KEY chưa cấu hình")
    try:
        parsed = parse_jd(query)
    except Exception as e:
        frappe.throw(str(e))
    return {"parsed_jd": parsed}
# ── Draft Document ────────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
def draft_document(
    candidate_info: str,
    doc_type: str = "invite_collab",
    org_name: str = "",
    sender_name: str = "",
    extra_note: str = "",
):
    """
    Soạn thảo văn bản mời ứng viên dựa trên thông tin ứng viên.
    
    Params:
        candidate_info: JSON string chứa thông tin ứng viên (name, school, expertise, ...)
        doc_type: Loại văn bản (invite_collab, invite_expert, invite_project, invite_lecture, consult_request, partnership)
        org_name: Tên đơn vị gửi
        sender_name: Người ký
        extra_note: Ghi chú thêm
    """
    if not gpt_client:
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    DRAFT_PROMPTS = {
        "invite_collab":   "Thư mời hợp tác nghiên cứu khoa học",
        "invite_expert":   "Thư mời tham gia hội đồng chuyên gia phản biện",
        "invite_project":  "Thư mời tham gia dự án nghiên cứu",
        "invite_lecture":  "Thư mời giảng dạy hoặc báo cáo chuyên đề",
        "consult_request": "Công văn đề nghị tư vấn chuyên môn",
        "partnership":     "Thư đề xuất hợp tác chiến lược dài hạn",
    }

    doc_label = DRAFT_PROMPTS.get(doc_type, "Thư mời hợp tác")
    org = org_name or "đơn vị chúng tôi"
    sender_line = f"Người ký: {sender_name}" if sender_name else ""
    extra_line = f"Lưu ý thêm: {extra_note}" if extra_note else ""

    prompt = f"""Bạn là chuyên viên soạn thảo văn bản hành chính - ngoại giao chuyên nghiệp.
Hãy soạn một "{doc_label}" bằng tiếng Việt, trang trọng, chuyên nghiệp và đầy đủ.

Thông tin ứng viên/chuyên gia cần mời:
{candidate_info}

Đơn vị gửi: {org}
{sender_line}
{extra_line}

Yêu cầu:
- Văn phong lịch sự, trang trọng, đúng phong cách văn bản hành chính Việt Nam
- Đề cập cụ thể đến lĩnh vực chuyên môn của ứng viên
- Có đầy đủ: Kính gửi, Nội dung chính, Lời kết, Ký tên
- Độ dài phù hợp (khoảng 200-350 từ)
- Để trống [ngày tháng], [địa điểm], [số điện thoại liên hệ] nếu chưa có thông tin"""

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        draft_text = response.choices[0].message.content
    except Exception as e:
        frappe.throw(f"GPT error: {str(e)}")

    return {
        "doc_type": doc_type,
        "doc_label": doc_label,
        "draft": draft_text,
    }


# ════════════════════════════════════════════════════════════════════
# CT Frappe Template — Session & Access Control
# ════════════════════════════════════════════════════════════════════

from ct_datalake.utils.activity_logger import ActivityLogger, Timer

_logger = ActivityLogger(prefix="DL", module="CT DataLake")


def _resolve_session(session_id: str) -> str:
    """Tìm session_name từ session_id. Fallback trả về chuỗi rỗng."""
    if not session_id:
        return ""
    try:
        rows = frappe.db.get_all(
            "DL Session",
            filters={"session_id": session_id},
            fields=["name"],
            limit=1,
            ignore_permissions=True,  # bắt buộc: bypass DocType read permission
        )
        return rows[0].name if rows else ""
    except Exception:
        return ""


@frappe.whitelist(allow_guest=False)
def get_context():
    """
    Entry point cho Frontend (initSession).
    - Xác thực quyền qua ct_agent_hub.check_app_access (cookie-based)
    - Tạo DL Session mới
    - Trả về csrf_token + session_id + user info
    """
    dept = ""
    role = ""
    try:
        from ct_agent_hub.api import check_app_access
        agents_data = check_app_access("ct_datalake")
        user_depts = agents_data.get("user_departments", [])
        dept = ",".join(user_depts) if user_depts else ""
        role = agents_data.get("user_role", "")
    except ImportError:
        pass  # ct_agent_hub chưa được cài đặt

    session_id   = str(uuid.uuid4())
    session_name = _logger.create_session(session_id, dept=dept, role=role)

    return {
        "csrf_token":   frappe.sessions.get_csrf_token(),
        "session_id":   session_id,
        "session_name": session_name,
        "user":         frappe.session.user,
        "full_name":    frappe.utils.get_fullname(frappe.session.user),
    }