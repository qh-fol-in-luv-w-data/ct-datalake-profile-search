import os
import json
from sentence_transformers import SentenceTransformer
import faiss
import fitz  # PyMuPDF
from openai import OpenAI

# ============================================================
# CONFIG – chỉnh tại đây
# ============================================================
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "sk-...")
GPT_MODEL       = "gpt-4o-mini"

BASE_PATH = os.path.dirname(__file__)

FAISS_IN        = os.path.join(BASE_PATH, "data", "index.faiss")
META_IN         = os.path.join(BASE_PATH, "data", "metadata.json")
FAISS_OUT       = os.path.join(BASE_PATH, "data", "index_out.faiss")
META_OUT        = os.path.join(BASE_PATH, "data", "metadata_out.json")

PDF_PATH        = "CT_VERSE_Tờ_trình_G600.pdf"

EMBED_MODEL     = "intfloat/multilingual-e5-base"
SCORE_THRESHOLD = 0.40   # ngưỡng cosine similarity
TOP_K           = 5      # số ứng viên trả về mỗi lĩnh vực


# ============================================================
# STEP 1+2 – Gộp: render PDF → gửi Vision → trả về keywords luôn
# 1 lần gọi API duy nhất cho mỗi trang, trang cuối trả JSON keywords
# ============================================================
VISION_PROMPT = """
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
- Liệt kê ĐỦ tất cả lĩnh vực trong bảng tờ trình
- Keywords phải là thuật ngữ kỹ thuật CỤ THỂ
  Ví dụ tốt: "sounding rocket propulsion trajectory simulation"
  Ví dụ xấu: "tên lửa", "rocket"
- Nếu tờ trình có nhiều trang, chỉ trả JSON một lần duy nhất ở cuối
- Không thêm text ngoài JSON
"""


def _pdf_to_base64_pages(pdf_path: str, dpi: int = 200) -> list[str]:
    """Render từng trang PDF thành PNG base64."""
    import base64
    doc   = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        pages.append(base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return pages


def extract_keywords(pdf_path: str, gpt_client: OpenAI) -> list[dict]:
    """
    Gửi toàn bộ trang PDF dưới dạng ảnh lên GPT-4o Vision.
    GPT đọc tờ trình và trả về JSON keywords của từng lĩnh vực — 1 lần gọi duy nhất.
    """
    print("\n📄 Render PDF thành ảnh...")
    pages_b64 = _pdf_to_base64_pages(pdf_path)
    print(f"  ✅ {len(pages_b64)} trang")

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

    print("🤖 Gửi lên GPT-4o Vision, đang chờ phân tích...")
    resp = gpt_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": content}]
    )

    result  = json.loads(resp.choices[0].message.content)
    domains = result.get("domains", [])

    print(f"  ✅ Tìm thấy {len(domains)} lĩnh vực:\n")
    for d in domains:
        print(f"  📌 {d['name']}")
        print(f"     VI: {d['query_vi']}")
        print(f"     EN: {d['query_en']}")

    return domains


# ============================================================
# STEP 3 – Load FAISS + Search
# ============================================================
def load_datasets() -> dict:
    datasets = {}

    if os.path.exists(FAISS_IN):
        datasets["in"] = {
            "index": faiss.read_index(FAISS_IN),
            "source": "Internal"
        }
    else:
        print(f"  ⚠️  Không tìm thấy {FAISS_IN} → bỏ qua mode=in")

    if os.path.exists(FAISS_OUT):
        datasets["out"] = {
            "index": faiss.read_index(FAISS_OUT),
            "source": "External"
        }
    else:
        print(f"  ⚠️  Không tìm thấy {FAISS_OUT} → bỏ qua mode=out")

    return datasets


def search_faiss(query: str, mode: str, datasets: dict,
                 embed_model: SentenceTransformer) -> list[dict]:
    """
    Search một query trong một FAISS index.
    Trả về list[{score, data, mode}].
    """
    import frappe
    
    if mode not in datasets:
        return []

    index = datasets[mode]["index"]
    db_source = datasets[mode]["source"]

    prefix = "query: research interests related to" if mode == "out" else "query:"
    q_vec  = embed_model.encode(
        [f"{prefix} {query}"],
        normalize_embeddings=True
    ).astype("float32")

    D, I = index.search(q_vec, TOP_K * 4)

    results = []
    seen    = set()

    for score, idx in zip(D[0], I[0]):
        if idx < 0:
            continue
        if score < SCORE_THRESHOLD:
            continue

        idx = int(idx)
        candidates = frappe.get_all("Candidate", filters={"faiss_id": idx, "source": db_source}, fields=["*"], limit=1)
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
                "trường họ và tên": candidate.candidate_name,
                "trường": candidate.affiliation,
                "học hàm": candidate.hoc_ham,
                "học vị": candidate.hoc_vi,
                "chức vụ": candidate.chuc_vu,
                "sản phẩm thực hiện": candidate.san_pham_thuc_hien
            }
            key = f"{candidate.candidate_name}|{candidate.affiliation}"

        if key in seen:
            continue
        seen.add(key)

        results.append({
            "score": round(float(score), 4),
            "data":  data_dict,
            "mode":  mode
        })

        if len(results) >= TOP_K:
            break

    return results


def search_domain(domain: dict, datasets: dict,
                  embed_model: SentenceTransformer) -> list[dict]:
    """
    Search cả in & out với cả query VI + EN.
    Gộp kết quả, loại trùng, sort theo score.
    """
    queries = [domain["query_vi"], domain["query_en"]]

    all_hits  = []
    seen_keys = set()

    for mode in datasets:
        for q in queries:
            for hit in search_faiss(q, mode, datasets, embed_model):
                d = hit["data"]
                if hit["mode"] == "out":
                    key = d.get("url") or f"{d.get('name')}|{d.get('affiliation')}"
                else:
                    key = f"{d.get('trường họ và tên')}|{d.get('trường')}"

                if key not in seen_keys:
                    seen_keys.add(key)
                    all_hits.append(hit)

    all_hits.sort(key=lambda x: x["score"], reverse=True)
    return all_hits[:TOP_K * 2]


# ============================================================
# STEP 4 – Hiển thị kết quả
# ============================================================
def display_candidate(hit: dict, rank: int):
    d    = hit["data"]
    mode = hit["mode"]
    src  = "🌐 Google Scholar" if mode == "out" else "🏫 Nội bộ"

    print(f"\n  #{rank}  {src}  [score={hit['score']}]")

    if mode == "out":
        interests = ", ".join(d.get("interests") or [])
        print(f"  Tên        : {d.get('name')}")
        print(f"  Đơn vị     : {d.get('affiliation')}")
        print(f"  Interests  : {interests}")
        print(f"  h-index    : {d.get('h_index')}  |  Citations: {d.get('citations')}")
        print(f"  URL        : {d.get('url')}")
    else:
        # ── FIX: dùng "trường họ và tên" thay vì "tên" / "name" ──
        print(f"  Tên        : {d.get('trường họ và tên')}")
        print(f"  Trường     : {d.get('trường')}")
        print(f"  Học hàm/vị : {d.get('học hàm')} / {d.get('học vị')}")
        print(f"  Chức vụ    : {d.get('chức vụ')}")
        sp = d.get('sản phẩm thực hiện', '')
        print(f"  Sản phẩm   : {str(sp)[:120]}")


# ============================================================
# MAIN
# ============================================================
def main():
    client = OpenAI(api_key=OPENAI_API_KEY)

    print("⏳ Load embedding model (lần đầu có thể mất vài phút)...")
    embed_model = SentenceTransformer(EMBED_MODEL)

    print("\n⏳ Load FAISS datasets...")
    datasets = load_datasets()
    if not datasets:
        print("❌ Không có FAISS index nào. Kiểm tra lại đường dẫn file.")
        return

    if not os.path.exists(PDF_PATH):
        print(f"❌ Không tìm thấy: {PDF_PATH}")
        return

    domains = extract_keywords(PDF_PATH, client)
    if not domains:
        print("❌ GPT không trích xuất được lĩnh vực nào.")
        return

    print("\n" + "=" * 65)
    print("     KẾT QUẢ ĐỀ XUẤT ỨNG VIÊN – DỰ ÁN G600")
    print("=" * 65)

    for domain in domains:
        print(f"\n{'─' * 65}")
        print(f"🔬  {domain['name'].upper()}")
        print(f"{'─' * 65}")

        hits = search_domain(domain, datasets, embed_model)

        if not hits:
            print("  ⚠️  Không tìm thấy ứng viên phù hợp (score thấp hơn ngưỡng)")
            continue

        for i, hit in enumerate(hits, 1):
            display_candidate(hit, i)

    print("\n" + "=" * 65)
    print("✅ Hoàn thành")
