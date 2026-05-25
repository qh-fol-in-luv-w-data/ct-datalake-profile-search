from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import frappe
import os
import json

# ========================
# CONFIG
# ========================
MODEL_NAME = "intfloat/multilingual-e5-base"
SCORE_THRESHOLD = 0.75

os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

BASE_PATH = os.path.dirname(__file__)

# ========================
# LOAD 2 MODE FAISS INDEX
# ========================
DATASETS = {
    "in": {
        "index": None,
        "metadata": None,
        "path": os.path.join(BASE_PATH, "data", "index.faiss"),
        "meta_path": os.path.join(BASE_PATH, "data", "metadata.json")
    },
    "out": {
        "index": None,
        "metadata": None,
        "path": os.path.join(BASE_PATH, "data", "index_out.faiss"),
        "meta_path": os.path.join(BASE_PATH, "data", "metadata_out.json")
    }
}

_indexes_loaded = False

def load_indexes():
    global _indexes_loaded
    if _indexes_loaded:
        return
    for mode, conf in DATASETS.items():
        if os.path.exists(conf["path"]):
            try:
                conf["index"] = faiss.read_index(conf["path"])
            except Exception as e:
                print(f"Warning: Could not read FAISS index for {mode}: {e}")
        if os.path.exists(conf["meta_path"]):
            try:
                with open(conf["meta_path"], "r", encoding="utf-8") as f:
                    conf["metadata"] = json.load(f)
            except Exception as e:
                print(f"Warning: Could not read metadata for {mode}: {e}")
    _indexes_loaded = True

# ========================
# SEARCH
# ========================
def search(query: str, mode: str = "in", top_k: int = 5):
    """
    mode:
        in  -> index.faiss + metadata.json (Internal)
        out -> index_out.faiss + metadata_out.json (External)
    """
    if mode not in DATASETS:
        raise ValueError("mode phải là 'in' hoặc 'out'")

    load_indexes()

    index = DATASETS[mode]["index"]
    metadata = DATASETS[mode]["metadata"]
    
    if index is None or metadata is None:
        return []

    query_lower = query.lower()

    # ---------- encode query ----------
    if mode == "out":
        q_text = f"query: research interests related to {query}"
    else:
        q_text = f"query: {query}"

    q_vec = get_model().encode(
        [q_text],
        normalize_embeddings=True
    ).astype("float32")

    D, I = index.search(q_vec, top_k * 5)

    if len(D[0]) == 0 or D[0][0] < SCORE_THRESHOLD:
        return []

    results = []
    seen = set()

    for score, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        if score < SCORE_THRESHOLD:
            break

        candidate = metadata[int(idx)]

        # Map to JSON dictionary format to avoid breaking API / jd_match logic
        if mode == "in":
            data_dict = {
                "họ và tên": candidate.get("trường họ và tên", ""),
                "trường họ và tên": candidate.get("trường họ và tên", ""),
                "trường": candidate.get("trường", ""),
                "học hàm": candidate.get("học hàm", ""),
                "học vị": candidate.get("học vị", ""),
                "chức vụ": candidate.get("chức vụ", ""),
                "sản phẩm thực hiện": candidate.get("sản phẩm thực hiện", "")
            }
            key = f"{data_dict['họ và tên']}||{data_dict['trường']}||{data_dict['chức vụ']}"
        else:
            data_dict = {
                "name": candidate.get("name", ""),
                "affiliation": candidate.get("affiliation", ""),
                "email": candidate.get("email", ""),
                "interests": candidate.get("interests", []),
                "citations": str(candidate.get("citations", 0)),
                "h_index": str(candidate.get("h_index", 0)),
                "url": candidate.get("url", ""),
                "city": candidate.get("city", ""),
                "university_abbr": candidate.get("university_abbr", ""),
                "university_name": candidate.get("university_name", "")
            }
            key = f"{data_dict['name']}||{data_dict['affiliation']}"

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