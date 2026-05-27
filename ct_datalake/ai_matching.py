import os
import json
import fitz  # PyMuPDF
from openai import OpenAI
import frappe
import redis
from redis.commands.search.query import Query

from .ct_datalake_config import (
    get_redis_host, get_redis_port, get_redis_password,
    get_redis_index_name,
)

# ============================================================
# CONFIG
# ============================================================
GPT_MODEL       = "gpt-4o-mini"

BASE_PATH = os.path.dirname(__file__)

TOP_K = 5      # sß╗æ ß╗⌐ng vi├¬n trß║ú vß╗ü mß╗ùi l─⌐nh vß╗▒c

def get_redis_client():
    pw = get_redis_password()
    return redis.Redis(
        host=get_redis_host(), 
        port=get_redis_port(), 
        password=pw or None, 
        db=0, 
        decode_responses=True
    )

# ============================================================
# STEP 1+2 ΓÇô Gß╗Öp: render PDF ΓåÆ gß╗¡i Vision ΓåÆ trß║ú vß╗ü keywords
# ============================================================
VISION_PROMPT = """
─É├óy l├á tß╗¥ tr├¼nh kß╗╣ thuß║¡t/h├ánh ch├¡nh. H├úy ─æß╗ìc TO├ÇN Bß╗ÿ nß╗Öi dung (kß╗â cß║ú bß║úng biß╗âu).

Trß║ú vß╗ü JSON (kh├┤ng k├¿m markdown):
{
  "domains": [
    {
      "name": "t├¬n l─⌐nh vß╗▒c chuy├¬n m├┤n",
      "keywords_vi": ["tß╗½ kh├│a kß╗╣ thuß║¡t tiß║┐ng Viß╗çt"],
      "keywords_en": ["specific technical keyword in English"],
      "query_vi": "chuß╗ùi query 6-8 tß╗½ kh├│a kß╗╣ thuß║¡t chuy├¬n s├óu tiß║┐ng Viß╗çt",
      "query_en": "English query string with 6-8 most specific technical keywords"
    }
  ]
}

L╞░u ├╜:
- Liß╗çt k├¬ ─Éß╗ª tß║Ñt cß║ú l─⌐nh vß╗▒c trong bß║úng tß╗¥ tr├¼nh
- Keywords phß║úi l├á thuß║¡t ngß╗» kß╗╣ thuß║¡t Cß╗ñ THß╗é
  V├¡ dß╗Ñ tß╗æt: "sounding rocket propulsion trajectory simulation"
  V├¡ dß╗Ñ xß║Ñu: "t├¬n lß╗¡a", "rocket"
- Nß║┐u tß╗¥ tr├¼nh c├│ nhiß╗üu trang, chß╗ë trß║ú JSON mß╗Öt lß║ºn duy nhß║Ñt ß╗ƒ cuß╗æi
- Kh├┤ng th├¬m text ngo├ái JSON
"""

def _pdf_to_base64_pages(pdf_path: str, dpi: int = 200) -> list[str]:
    import base64
    doc   = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        pages.append(base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return pages

def extract_keywords(pdf_path: str, gpt_client: OpenAI) -> list[dict]:
    print("\n≡ƒôä Render PDF th├ánh ß║únh...")
    pages_b64 = _pdf_to_base64_pages(pdf_path)
    print(f"  Γ£à {len(pages_b64)} trang")

    content = []
    for i, b64 in enumerate(pages_b64, 1):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high"
            }
        })

    content.append({"type": "text", "text": VISION_PROMPT})

    print("≡ƒñû Gß╗¡i l├¬n GPT-4o Vision, ─æang chß╗¥ ph├ón t├¡ch...")
    resp = gpt_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": content}]
    )

    result  = json.loads(resp.choices[0].message.content)
    domains = result.get("domains", [])

    print(f"  Γ£à T├¼m thß║Ñy {len(domains)} l─⌐nh vß╗▒c:\n")
    for d in domains:
        print(f"  ≡ƒôî {d['name']}")
        print(f"     VI: {d['query_vi']}")
        print(f"     EN: {d['query_en']}")

    return domains


# ============================================================
# STEP 3 ΓÇô REDIS SEARCH
# ============================================================
def search_redis(query: str, mode: str, client: redis.Redis) -> list[dict]:
    """
    Search mß╗Öt query trong RediSearch index.
    Trß║ú vß╗ü list[{score, data, mode}].
    """
    if mode not in ["in", "out"]:
        return []

    db_source = "Internal" if mode == "in" else "External"

    # X├│a k├╜ tß╗▒ ─æß║╖c biß╗çt
    safe_query = query.replace("(", "").replace(")", "").replace(":", "").replace("-", " ")
    
    # K├╜ hiß╗çu | gi├║p t├¼m theo OR
    words = [w for w in safe_query.split() if w.strip()]
    or_query = " | ".join(words) if words else ""
    
    redis_query_str = f"(@source:{{{db_source}}}) ({or_query})"
    q = Query(redis_query_str).paging(0, TOP_K * 4).with_scores()

    try:
        res = client.ft(get_redis_index_name()).search(q)
    except Exception as e:
        print("Γ¥î Lß╗ùi truy vß║Ñn RediSearch:", e)
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
                "hß╗ì v├á t├¬n": candidate.candidate_name,
                "tr╞░ß╗¥ng hß╗ì v├á t├¬n": candidate.candidate_name,
                "tr╞░ß╗¥ng": candidate.affiliation,
                "hß╗ìc h├ám": candidate.hoc_ham,
                "hß╗ìc vß╗ï": candidate.hoc_vi,
                "chß╗⌐c vß╗Ñ": candidate.chuc_vu,
                "sß║ún phß║⌐m thß╗▒c hiß╗çn": candidate.san_pham_thuc_hien
            }
            key = f"{candidate.candidate_name}|{candidate.affiliation}"

        if key in seen:
            continue
        seen.add(key)

        results.append({
            "score": round(score, 4),
            "data":  data_dict,
            "mode":  mode
        })

        if len(results) >= TOP_K:
            break

    return results


def search_domain(domain: dict, client: redis.Redis) -> list[dict]:
    """
    Search cß║ú in & out vß╗¢i cß║ú query VI + EN bß║▒ng Redis.
    Gß╗Öp kß║┐t quß║ú, loß║íi tr├╣ng, sort theo score (score lß╗¢n h╞ín l├á match h╞ín).
    """
    queries = [domain["query_vi"], domain["query_en"]]
    all_hits  = []
    seen_keys = set()

    for mode in ["in", "out"]:
        for q in queries:
            for hit in search_redis(q, mode, client):
                d = hit["data"]
                if hit["mode"] == "out":
                    key = d.get("url") or f"{d.get('name')}|{d.get('affiliation')}"
                else:
                    key = f"{d.get('tr╞░ß╗¥ng hß╗ì v├á t├¬n')}|{d.get('tr╞░ß╗¥ng')}"

                if key not in seen_keys:
                    seen_keys.add(key)
                    all_hits.append(hit)

    # RediSearch text score c├áng lß╗¢n c├áng match tß╗æt
    all_hits.sort(key=lambda x: x["score"], reverse=True)
    return all_hits[:TOP_K * 2]


# ============================================================
# STEP 4 ΓÇô Hiß╗ân thß╗ï kß║┐t quß║ú
# ============================================================
def display_candidate(hit: dict, rank: int):
    d    = hit["data"]
    mode = hit["mode"]
    src  = "≡ƒîÉ Google Scholar" if mode == "out" else "≡ƒÅ½ Nß╗Öi bß╗Ö"

    print(f"\n  #{rank}  {src}  [score={hit['score']}]")

    if mode == "out":
        interests = ", ".join(d.get("interests") or [])
        print(f"  T├¬n        : {d.get('name')}")
        print(f"  ─É╞ín vß╗ï     : {d.get('affiliation')}")
        print(f"  Interests  : {interests}")
        print(f"  h-index    : {d.get('h_index')}  |  Citations: {d.get('citations')}")
        print(f"  URL        : {d.get('url')}")
    else:
        print(f"  T├¬n        : {d.get('tr╞░ß╗¥ng hß╗ì v├á t├¬n')}")
        print(f"  Tr╞░ß╗¥ng     : {d.get('tr╞░ß╗¥ng')}")
        print(f"  Hß╗ìc h├ám/vß╗ï : {d.get('hß╗ìc h├ám')} / {d.get('hß╗ìc vß╗ï')}")
        print(f"  Chß╗⌐c vß╗Ñ    : {d.get('chß╗⌐c vß╗Ñ')}")
        sp = d.get('sß║ún phß║⌐m thß╗▒c hiß╗çn', '')
        print(f"  Sß║ún phß║⌐m   : {str(sp)[:120]}")
