import frappe
import os
import redis
import requests
from redis.commands.search.query import Query
from pathlib import Path
from dotenv import load_dotenv

# Load .env
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# ========================
# CONFIG
# ========================
REDIS_HOST        = "localhost"
REDIS_PORT        = 6399    # Redis Stack local (mode=in)
INDEX_NAME        = "idx:candidate"
EXTERNAL_API_KEY   = os.getenv("EXTERNAL_API_KEY", "")
EXTERNAL_API_URL   = os.getenv("EXTERNAL_API_URL", "http://103.186.101.219/api/professors")
EXTERNAL_FTS_URL   = os.getenv("EXTERNAL_FTS_URL", "http://103.186.101.219/api/search/professors")
INTERNAL_API_URL   = os.getenv("INTERNAL_FTS_URL", "http://103.186.101.219/api/search/experts")


def _get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


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
            EXTERNAL_FTS_URL,
            headers={"X-API-Key": EXTERNAL_API_KEY},
            params={"q": query, "limit": top_k},
            timeout=10,
        )
        resp.raise_for_status()
        data  = resp.json()
        # Server trß║ú vß╗ü {"total": N, "results": [...]} hoß║╖c list trß╗▒c tiß║┐p
        items = data.get("results", data) if isinstance(data, dict) else data
    except Exception as e:
        frappe.logger().warning(f"[search] External FTS error: {e}")
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
            INTERNAL_API_URL,
            headers={"X-API-Key": EXTERNAL_API_KEY},
            params={"q": query, "limit": top_k},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json()
        if isinstance(items, dict):
            items = items.get("results", items.get("data", []))
    except Exception as e:
        frappe.logger().warning(f"[search] Internal API error: {e}")
        return []

    results = []
    for item in items:
        results.append({
            "score": item.get("score", 0.0),
            "data": {
                "id":               item.get("id", ""),
                "m├ú sß╗æ":            item.get("code", ""),
                "hß╗ì v├á t├¬n":        item.get("name", ""),
                "chuy├¬n ng├ánh":     item.get("specialization", ""),
                "khoa/ph├▓ng ban":   item.get("department", ""),
                "hß╗ìc h├ám":          item.get("academic_rank", ""),
                "hß╗ìc vß╗ï":           item.get("degree", ""),
                "email":            item.get("email", ""),
                "─æiß╗çn thoß║íi":       item.get("phone", ""),
                "trß║íng th├íi":       item.get("active_status", ""),
                "mß╗⌐c hß╗úp t├íc":      item.get("cooperation_level", ""),
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
        raise ValueError("mode phß║úi l├á 'in' hoß║╖c 'out'")

    if mode == "out":
        return _search_external(query, top_k)

    return _search_internal(query, top_k)
