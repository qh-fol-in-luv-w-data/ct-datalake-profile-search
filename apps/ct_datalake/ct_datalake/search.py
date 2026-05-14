from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import frappe
import os

# ========================
# CONFIG
# ========================
MODEL_NAME = "intfloat/multilingual-e5-base"
SCORE_THRESHOLD = 0.75
model = SentenceTransformer(MODEL_NAME)

BASE_PATH = os.path.dirname(__file__)

# ========================
# LOAD 2 MODE FAISS INDEX
# ========================
DATASETS = {
    "in": {
        "index": faiss.read_index(os.path.join(BASE_PATH, "index.faiss")),
        "source": "Internal"
    },
    "out": {
        "index": faiss.read_index(os.path.join(BASE_PATH, "index_out.faiss")),
        "source": "External"
    }
}

# ========================
# SEARCH
# ========================
def search(query: str, mode: str = "in", top_k: int = 5):
    """
    mode:
        in  -> index.faiss + DB (Internal)
        out -> index_out.faiss + DB (External)
    """
    if mode not in DATASETS:
        raise ValueError("mode phải là 'in' hoặc 'out'")

    index = DATASETS[mode]["index"]
    db_source = DATASETS[mode]["source"]
    query_lower = query.lower()

    # ---------- encode query ----------
    if mode == "out":
        q_text = f"query: research interests related to {query}"
    else:
        q_text = f"query: {query}"

    q_vec = model.encode(
        [q_text],
        normalize_embeddings=True
    ).astype("float32")

    D, I = index.search(q_vec, top_k * 5)

    if len(D[0]) == 0 or D[0][0] < SCORE_THRESHOLD:
        return []

    results = []
    seen = set()

    for score, idx in zip(D[0], I[0]):
        if idx < 0:
            continue
        if score < SCORE_THRESHOLD:
            break

        # Query Frappe DB
        idx = int(idx)
        # Using faiss_id to find the candidate
        # Since faiss_id might not be unique globally if we have two sources, we use source filter too.
        candidates = frappe.get_all("Candidate", filters={"faiss_id": idx, "source": db_source}, fields=["*"], limit=1)
        
        if not candidates:
            continue
            
        candidate = candidates[0]

        # No strict keyword filtering as FAISS (multilingual-e5) handles semantic matching across languages.

        # Map to old JSON dictionary format to avoid breaking API / jd_match logic
        if mode == "in":
            data_dict = {
                "họ và tên": candidate.candidate_name,
                "trường họ và tên": candidate.candidate_name,
                "trường": candidate.affiliation,
                "học hàm": candidate.hoc_ham,
                "học vị": candidate.hoc_vi,
                "chức vụ": candidate.chuc_vu,
                "sản phẩm thực hiện": candidate.san_pham_thuc_hien
            }
            key = f"{candidate.candidate_name}||{candidate.affiliation}||{candidate.chuc_vu}"
        else:
            data_dict = {
                "name": candidate.candidate_name,
                "affiliation": candidate.affiliation,
                "email": candidate.email,
                "interests": candidate.interests.split(", ") if candidate.interests else [],
                "citations": candidate.citations,
                "h_index": candidate.h_index,
                "url": candidate.scholar_url,
                "city": candidate.city,
                "university_abbr": "", # we didn't save this separately
                "university_name": candidate.affiliation # map to affiliation
            }
            key = f"{candidate.candidate_name}||{candidate.affiliation}"

        if key in seen:
            continue
        seen.add(key)

        results.append({
            "score": float(score),
            "data": data_dict
        })

        if len(results) >= top_k:
            break

    return results

if __name__ == "__main__":
    pass