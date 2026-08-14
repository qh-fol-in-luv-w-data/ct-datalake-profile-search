import frappe
import os
import json
import uuid
import tempfile
import hashlib
from typing import Literal, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Load .env từ thư mục gốc của app (ct_datalake/)
_env_path = Path(__file__).resolve().parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# ─── internal modules ───────────────────────────────────────────────
from .search import search as bm25_search
from .llm_rerank import rerank
from .jd_match import (
    match_jd,
    normalize_candidate,
    parse_jd,
    extract_text_from_upload as _extract_text,
)
from .ai_matching import extract_keywords, search_domain, get_redis_client
from openai import OpenAI
from .openai_key import get_openai_client
from . import ai_matching as _rc

# ─── OpenAI client ──────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════
# ROUTES (Frappe Whitelisted)
# ════════════════════════════════════════════════════════════════════

# ── Health check ────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False)
def root():
    """Kiểm tra trạng thái API"""
    return {
        "status": "ok",
        "service": "AI Candidate Search API (Frappe)",
        "version": "1.0.0",
        "endpoints": [
            "/api/method/ct_datalake.api.root",
            "/api/method/ct_datalake.api.health",
            "/api/method/ct_datalake.api.semantic_search",
            "/api/method/ct_datalake.api.semantic_search_llm",
            "/api/method/ct_datalake.api.jd_match",
            "/api/method/ct_datalake.api.jd_match_upload",
            "/api/method/ct_datalake.api.jd_analyze",
            "/api/method/ct_datalake.api.g600_analyze",
            "/api/method/ct_datalake.api.jd_parse_only",
            "/api/method/ct_datalake.api.draft_document",
            "/api/method/ct_datalake.api.get_context",
        ],
    }

@frappe.whitelist(allow_guest=False)
def health():
    """Health check chi tiết"""
    return {
        "status": "healthy",
        "openai_configured": bool(get_openai_client()),
    }

# ── Semantic Search (FAISS) ─────────────────────────────────────────
@frappe.whitelist(allow_guest=False)
def semantic_search(query: str, mode: str = "in", top_k: int = 5):
    """
    Tìm kiếm ứng viên BM25:
      mode=in  → Internal (local Redis + Frappe DB)
      mode=out → External (server Redis Stack + synonyms)
    """
    cache_key = f"semantic_search_{hashlib.sha256(f'{query}_{mode}_{top_k}'.encode()).hexdigest()}"
    
    use_cache = str(frappe.form_dict.get("use_cache", "1"))
    if use_cache == "1":
        cached = frappe.cache().get_value(cache_key)
        if cached:
            frappe.response["use_cache"] = 1
            return cached

    frappe.response["use_cache"] = 0
    try:
        top_k = int(top_k)
        raw = bm25_search(query=query, mode=mode, top_k=top_k)
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

    result = {
        "query": query,
        "mode": mode,
        "total": len(results),
        "results": results,
    }
    frappe.cache().set_value(cache_key, result, expires_in_sec=86400)
    return result

# ── Semantic Search (LLM Rerank) ────────────────────────────────────
@frappe.whitelist(allow_guest=False)
def semantic_search_llm(query: str, mode: str = "in", top_k: int = 5):
    """
    BM25 search rồi đưa kết quả vào LLM server-side để phân tích.
    """
    cache_key = f"semantic_search_llm_{hashlib.sha256(f'{query}_{mode}_{top_k}'.encode()).hexdigest()}"
    
    use_cache = str(frappe.form_dict.get("use_cache", "1"))
    if use_cache == "1":
        cached = frappe.cache().get_value(cache_key)
        if cached:
            frappe.response["use_cache"] = 1
            return cached

    frappe.response["use_cache"] = 0
    if not get_openai_client():
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    try:
        top_k = int(top_k)
        raw = bm25_search(
            query=query,
            mode=mode,
            top_k=max(top_k * 2, 10)
        )
    except Exception as e:
        frappe.throw(f"Search error: {str(e)}")

    if not raw:
        return {"query": query, "mode": mode, "total_found": 0, "llm_analysis": ""}

    try:
        session_name, action_name = get_current_session_info()
        analysis = rerank(query=query, candidates=raw[:top_k], mode=mode, session_info=(session_name, action_name))
    except Exception as e:
        frappe.throw(f"LLM rerank error: {str(e)}")

    result = {
        "query": query,
        "mode": mode,
        "total_found": len(raw),
        "candidates_sent_to_llm": top_k,
        "llm_analysis": analysis,
    }
    frappe.cache().set_value(cache_key, result, expires_in_sec=86400)
    return result

# ── JD Matching (via form fields) ───────────────────────────────────
@frappe.whitelist(allow_guest=False)
def jd_match(jd_text: str, mode: str = "in", top_k: int = 5, fast: bool = False):
    """
    Match JD với ứng viên.
    """
    if not get_openai_client() and not frappe.parse_json(fast):
        frappe.throw("OPENAI_API_KEY chưa cấu hình. Dùng fast=true để chỉ dùng RediSearch.")

    try:
        top_k = int(top_k)
        fast = frappe.parse_json(fast)
        session_name, action_name = get_current_session_info()
        result = match_jd(
            jd_text=jd_text,
            mode=mode,
            top_k=top_k,
            fast=fast,
            session_info=(session_name, action_name)
        )
    except Exception as e:
        frappe.throw(f"JD match error: {str(e)}")

    return {
        "parsed_jd": result.get("parsed_jd", {}),
        "total_found": result.get("total_found", 0),
        "candidates": result.get("candidates", []),
    }

# ── JD Matching (File Upload) ───────────────────────────────────────
@frappe.whitelist(allow_guest=False)
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
        session_name, action_name = get_current_session_info()
        result = match_jd(
            jd_text=jd_text,
            mode=mode,
            top_k=top_k,
            fast=fast,
            session_info=(session_name, action_name)
        )
    except Exception as e:
        frappe.throw(f"JD match error: {str(e)}")

    return {
        "parsed_jd": result.get("parsed_jd", {}),
        "total_found": result.get("total_found", 0),
        "candidates": result.get("candidates", []),
    }

# ── JD Analysis (All-in-one with Vision + Local Redis) ───────────────
@frappe.whitelist(allow_guest=False)
def jd_analyze():
    """
    Upload JD PDF → GPT-4o Vision trích xuất → Search trực tiếp Local Redis → GPT-4o rerank & giải thích.
    """
    if not get_openai_client():
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    if not frappe.request.files:
        frappe.throw("Chưa có file nào được upload")

    file = frappe.request.files.get("file")
    if not file:
        frappe.throw("Vui lòng upload file với key 'file'")

    source = frappe.form_dict.get("source", "in")
    top_k = int(frappe.form_dict.get("top_k", 5))

    if not (file.filename or "").lower().endswith(".pdf"):
        frappe.throw("Chỉ chấp nhận file PDF cho tính năng đọc trực tiếp bằng AI Vision")

    file_bytes = file.stream.read()

    import hashlib
    hash_sha256 = hashlib.sha256()
    hash_sha256.update(file_bytes)
    hash_sha256.update(source.encode())
    hash_sha256.update(str(top_k).encode())
    cache_key = f"jd_analyze_{hash_sha256.hexdigest()}"
    
    use_cache = str(frappe.form_dict.get("use_cache", "1"))
    if use_cache == "1":
        cached = frappe.cache().get_value(cache_key)
        if cached:
            frappe.response["use_cache"] = 1
            return cached

    frappe.response["use_cache"] = 0
    # 1. Ghi PDF tạm thời
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # 2. Extract yêu cầu bằng Vision
    try:
        parsed_jd = _rc.extract_jd_requirements(tmp_path, get_openai_client())
    except Exception as e:
        frappe.throw(f"GPT Vision error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not parsed_jd:
        frappe.throw("GPT không thể đọc được JD")

    # 3. Kết nối Local Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
    except Exception:
        frappe.throw("Không thể kết nối đến Redis Stack")

    _rc.TOP_K = top_k
    
    keywords = parsed_jd.get("keywords", [])
    domain = parsed_jd.get("domain", "")
    summary = parsed_jd.get("summary", "")
    
    queries = list(dict.fromkeys(filter(None, [
        domain,
        *keywords,
    ])))

    # 4. Tìm kiếm cục bộ (FAISS/BM25)
    all_hits = []
    seen_keys = set()
    modes = ["in", "out"] if source == "both" else [source]
    
    for m in modes:
        for q in queries:
            if not q.strip(): continue
            hits = bm25_search(q, mode=m, top_k=_rc.TOP_K * 4)
            for h in hits: h["mode"] = m
            for hit in hits:
                d = hit["data"]
                if hit["mode"] == "out":
                    key = d.get("url") or f"{d.get('name')}|{d.get('affiliation')}"
                else:
                    key = f"{d.get('họ và tên', d.get('trường họ và tên'))}|{d.get('trường')}"
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_hits.append(hit)

    # Lọc lấy top các ứng viên (gấp 3 lần top_k để LLM chấm)
    all_hits.sort(key=lambda x: x["score"], reverse=True)
    raw_candidates = all_hits[: top_k * 3]

    if not raw_candidates:
        return []

    # 5. Dùng LLM Rerank và Giải thích chuyên môn
    jd_summary_text = f"Summary: {summary}\nDomain: {domain}\nSkills: {', '.join(parsed_jd.get('required_skills', []))}"
    
    from .jd_match import _rerank_candidates
    
    ranked_candidates = _rerank_candidates(
        jd_text=jd_summary_text,
        parsed_jd=parsed_jd,
        candidates=raw_candidates,
        mode="in" if source == "both" else source,
        top_k=top_k
    )

    frappe.cache().set_value(cache_key, ranked_candidates, expires_in_sec=86400)
    return ranked_candidates

# ── G600 PDF Analysis ────────────────────────────────────────────────
# ── G600 PDF Analysis ────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False)
def g600_analyze():
    """
    Upload JD PDF → GPT-4o Vision trích xuất → Search trực tiếp Local Redis → GPT-4o rerank & giải thích.
    """
    if not get_openai_client():
        frappe.throw("OPENAI_API_KEY chưa được cấu hình")

    if not frappe.request.files:
        frappe.throw("Chưa có file nào được upload")

    file = frappe.request.files.get("file")
    if not file:
        frappe.throw("Vui lòng upload file với key 'file'")

    source = frappe.form_dict.get("source", "in")
    top_k = int(frappe.form_dict.get("top_k", 5))

    if not (file.filename or "").lower().endswith(".pdf"):
        frappe.throw("Chỉ chấp nhận file PDF cho tính năng đọc trực tiếp bằng AI Vision")

    file_bytes = file.stream.read()

    import hashlib
    hash_sha256 = hashlib.sha256()
    hash_sha256.update(file_bytes)
    hash_sha256.update(source.encode())
    hash_sha256.update(str(top_k).encode())
    cache_key = f"g600_analyze_{hash_sha256.hexdigest()}"
    
    use_cache = str(frappe.form_dict.get("use_cache", "1"))
    if use_cache == "1":
        cached = frappe.cache().get_value(cache_key)
        if cached:
            frappe.response["use_cache"] = 1
            return cached

    frappe.response["use_cache"] = 0
    # 1. Ghi PDF tạm thời
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # 2. Extract yêu cầu bằng Vision
    try:
        parsed_jd = _rc.extract_jd_requirements(tmp_path, get_openai_client())
    except Exception as e:
        frappe.throw(f"GPT Vision error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not parsed_jd:
        frappe.throw("GPT không thể đọc được JD")

    # 3. Kết nối Local Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
    except Exception:
        frappe.throw("Không thể kết nối đến Redis Stack")

    _rc.TOP_K = top_k
    
    keywords = parsed_jd.get("keywords", [])
    domain = parsed_jd.get("domain", "")
    summary = parsed_jd.get("summary", "")
    
    queries = list(dict.fromkeys(filter(None, [
        domain,
        *keywords,
    ])))

    # 4. Tìm kiếm cục bộ (FAISS/BM25)
    all_hits = []
    seen_keys = set()
    modes = ["in", "out"] if source == "both" else [source]
    
    for m in modes:
        for q in queries:
            if not q.strip(): continue
            hits = bm25_search(q, mode=m, top_k=_rc.TOP_K * 4)
            for h in hits: h["mode"] = m
            for hit in hits:
                d = hit["data"]
                if hit["mode"] == "out":
                    key = d.get("url") or f"{d.get('name')}|{d.get('affiliation')}"
                else:
                    key = f"{d.get('họ và tên', d.get('trường họ và tên'))}|{d.get('trường')}"
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_hits.append(hit)

    # Lọc lấy top các ứng viên (gấp 3 lần top_k để LLM chấm)
    all_hits.sort(key=lambda x: x["score"], reverse=True)
    raw_candidates = all_hits[: top_k * 3]

    if not raw_candidates:
        return []

    # 5. Dùng LLM Rerank và Giải thích chuyên môn
    jd_summary_text = f"Summary: {summary}\nDomain: {domain}\nSkills: {', '.join(parsed_jd.get('required_skills', []))}"
    
    from .jd_match import _rerank_candidates
    
    ranked_candidates = _rerank_candidates(
        jd_text=jd_summary_text,
        parsed_jd=parsed_jd,
        candidates=raw_candidates,
        mode="in" if source == "both" else source,
        top_k=top_k
    )

    frappe.cache().set_value(cache_key, ranked_candidates, expires_in_sec=86400)
    return ranked_candidates



# ── Parse JD only ────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False)
def jd_parse_only(query: str):
    """
    Gửi JD text → GPT phân tích.
    """
    if not get_openai_client():
        frappe.throw("OPENAI_API_KEY chưa cấu hình")
    try:
        session_name, action_name = get_current_session_info()
        parsed = parse_jd(query, session_info=(session_name, action_name))
    except Exception as e:
        frappe.throw(str(e))
    return {"parsed_jd": parsed}
# ── Draft Document ────────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False)
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
    if not get_openai_client():
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
        response = get_openai_client().chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        draft_text = response.choices[0].message.content
        
        # Log token usage
        session_name, action_name = get_current_session_info()
        if session_name:
            if hasattr(response, "usage") and response.usage:
                _logger.log_ai_call(
                    session_name=session_name,
                    action_name=action_name,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
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

def get_current_session_info():
    session_id = frappe.get_request_header("X-Session-Id") or frappe.form_dict.get("session_id")
    action_name = frappe.get_request_header("X-Action-Name") or frappe.form_dict.get("action_name") or "Search LLM"
    session_name = _resolve_session(session_id) if session_id else ""
    return session_name, action_name

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
        try:
            from ct_agent_hub.api.core import check_app_access
        except ImportError:
            from ct_agent_hub.api import check_app_access

        agents_data = check_app_access("2as-master-profile")
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

