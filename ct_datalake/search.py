import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import frappe
import os
import redis
import requests
from redis.commands.search.query import Query

from .ct_datalake_config import (
    get_redis_host, get_redis_port, get_redis_password,
    get_redis_index_name,
    get_external_api_key, get_external_api_url,
    get_external_fts_url, get_internal_api_url,
)


def _get_redis():
    pw = get_redis_password()
    return redis.Redis(
        host=get_redis_host(),
        port=get_redis_port(),
        password=pw or None,
        db=0,
        decode_responses=True,
    )



def _build_redis_query(query: str, source: str, limit: int) -> Query:
    """Tß║ío BM25 OR-query cho RediSearch, lß╗ìc theo source tag."""
    safe  = query.replace("(","").replace(")","").replace(":","").replace("-"," ")
    words = [w for w in safe.split() if w.strip()]
    or_q  = " | ".join(words) if words else "*"
    return Query(f"(@source:{{{source}}}) ({or_q})").paging(0, limit).with_scores()


def _normalize(docs):
    """Chuß║⌐n h├│a BM25 score vß╗ü thang 0-1."""
    if not docs:
        return []
    max_score = float(docs[0].score) or 1.0
    return [(round(float(d.score) / max_score, 4), d) for d in docs]


# ========================
# MODE = OUT: gß╗ìi server /professors/fts
# ========================
def _search_external(query: str, top_k: int) -> list:
    """Gß╗ìi BM25 search endpoint tr├¬n server (Redis Stack + synonyms server-side)."""
    try:
        resp = requests.get(
            get_external_fts_url(),
            headers={
                "X-API-Key": get_external_api_key(),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            params={"q": query, "limit": top_k},
            timeout=10, verify=True,
        )
        resp.raise_for_status()
        data  = resp.json()
        # Server trß║ú vß╗ü {"total": N, "results": [...]} hoß║╖c list trß╗▒c tiß║┐p
        items = data.get("results", data) if isinstance(data, dict) else data
    except Exception as e:
        frappe.log_error(title="[search] External FTS error", message=str(e))
        # Do not throw exception to prevent breaking the flow
        return []

    return [
        {
            "score": item.get("score", 0.0),
            "data": {
                "name":            item.get("name", ""),
                "affiliation":     item.get("affiliation", ""),
                "email":           item.get("email", ""),
                "interests":       item.get("interests", []),
                "citations":       item.get("citations", 0),
                "h_index":         item.get("h_index", 0),
                "url":             item.get("url", ""),
                "city":            item.get("city", ""),
                "university_abbr": item.get("university_abbr", ""),
                "university_name": item.get("university_name", ""),
            },
        }
        for item in items
    ]


# ========================
# MODE = IN: gß╗ìi server /professors/experts
# ========================
def _search_internal(query: str, top_k: int) -> list:
    """T├¼m kiß║┐m nß╗Öi bß╗Ö: gß╗ìi /professors/experts tr├¬n server."""
    try:
        resp = requests.get(
            get_internal_api_url(),
            headers={
                "X-API-Key": get_external_api_key(),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            params={"q": query, "limit": top_k},
            timeout=10, verify=True,
        )
        resp.raise_for_status()
        items = resp.json()
        if isinstance(items, dict):
            items = items.get("results", items.get("data", []))
    except Exception as e:
        url_called = get_internal_api_url()
        frappe.log_error(title="[search] Internal API error", message=f"URL: {url_called}\nError: {str(e)}")
        frappe.throw(f"Lỗi khi gọi API tìm kiếm nội bộ ({url_called}): {str(e)}")

    results = []
    for item in items:
        results.append({
            "score": item.get("score", 0.0),
            "data": {
                "id":               item.get("id", ""),
                "mã số":            item.get("code", ""),
                "họ và tên":        item.get("name", ""),
                "chuyên ngành":     item.get("specialization", ""),
                "khoa/phòng ban":   item.get("department", ""),
                "học hàm":          item.get("academic_rank", ""),
                "học vị":           item.get("degree", ""),
                "email":            item.get("email", ""),
                "điện thoại":       item.get("phone", ""),
                "trạng thái":       item.get("active_status", ""),
                "mức hợp tác":      item.get("cooperation_level", ""),
            },
        })
    return results


# ========================
# PUBLIC API
# ========================
def search(query: str, mode: str = "in", top_k: int = 5) -> list:
    """
    T├¼m kiß║┐m BM25 theo mode:
        in  ΓåÆ Internal candidates (local Redis + Frappe DB)
        out ΓåÆ External professors (server Redis Stack + synonyms)
    """
    if mode not in ("in", "out"):
        raise ValueError("mode phải là 'in' hoặc 'out'")

    if mode == "out":
        return _search_external(query, top_k)

    return _search_internal(query, top_k)
