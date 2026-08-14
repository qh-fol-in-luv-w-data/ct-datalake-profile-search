"""
ct_datalake_config.py — Đọc config từ CT DataLake Settings DocType
===================================================================
Ưu tiên: DocType > .env > default
OpenAI key KHÔNG nằm ở đây — dùng openai_key.py (đọc từ Agent DocType).
"""
import frappe
import os


def _get_settings():
    """Lấy CT DataLake Settings (singleton). Cache per-request."""
    try:
        return frappe.get_cached_doc("CT DataLake Settings")
    except Exception:
        return None


def get_redis_host() -> str:
    s = _get_settings()
    if s and s.redis_host:
        return s.redis_host
    return os.getenv("REDIS_HOST", "localhost")


def get_redis_port() -> int:
    s = _get_settings()
    if s and s.redis_port:
        return int(s.redis_port)
    return int(os.getenv("REDIS_PORT", "6379"))


def get_redis_password() -> str:
    s = _get_settings()
    if s:
        try:
            pw = s.get_password("redis_password") or ""
            return pw
        except Exception:
            pass
    return os.getenv("REDIS_PASSWORD", "")


def get_redis_index_name() -> str:
    s = _get_settings()
    if s and s.redis_index_name:
        return s.redis_index_name
    return os.getenv("REDIS_INDEX_NAME", "idx:candidate")


def get_external_api_key() -> str:
    s = _get_settings()
    if s:
        try:
            key = s.get_password("external_api_key") or ""
            if key:
                return key
        except Exception:
            pass
    # Fallback API key nếu chưa config trong hệ thống
    return os.getenv("EXTERNAL_API_KEY", "")


def get_external_api_url() -> str:
    s = _get_settings()
    if s and s.external_api_url:
        return s.external_api_url
    return os.getenv("EXTERNAL_API_URL", "https://api.ctpai.vn/api/professors")


def get_external_fts_url() -> str:
    s = _get_settings()
    if s and s.external_fts_url:
        return s.external_fts_url
    return os.getenv("EXTERNAL_FTS_URL", "https://api.ctpai.vn/api/search/professors")


def get_internal_api_url() -> str:
    s = _get_settings()
    if s and s.internal_api_url:
        return s.internal_api_url
    return os.getenv("INTERNAL_FTS_URL", "https://api.ctpai.vn/api/search/experts")
