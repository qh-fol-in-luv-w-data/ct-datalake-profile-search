import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-base"

model = SentenceTransformer(MODEL_NAME)


# ========================
# UTILS
# ========================
def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return "" if x == 0 else str(x)
    return str(x).strip()


# ========================
# LOAD DATA
# ========================
with open("danh_sach_giao_su_tien_si_chuyen_gia_v5.json", "r", encoding="utf-8") as f:
    data = json.load(f)


# ========================
# DEDUPE
# ========================
seen = set()
clean_data = []

for item in data:
    key = (
        safe_str(item.get("trường họ và tên")),
        safe_str(item.get("trường")),
        safe_str(item.get("chức vụ"))
    )

    if key not in seen:
        seen.add(key)
        clean_data.append(item)

data = clean_data

print(f"✅ Data after dedupe: {len(data)} records")


# ========================
# BUILD TEXT
# ========================
texts = []
metadata = []

for item in data:
    text = f"""
    Tên: {safe_str(item.get("họ và tên"))}
    Trường: {safe_str(item.get("trường"))}
    Học hàm: {safe_str(item.get("học hàm"))}
    Học vị: {safe_str(item.get("học vị"))}
    Chức vụ: {safe_str(item.get("chức vụ"))}
    Lĩnh vực: {safe_str(item.get("sản phẩm thực hiện"))}
    """

    # 🔥 E5 requires prefix
    text = "passage: " + text.strip()

    texts.append(text)
    metadata.append(item)


# ========================
# ENCODE
# ========================
embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=True
)

embeddings = np.array(embeddings).astype("float32")


# ========================
# FAISS (COSINE)
# ========================
dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)
index.add(embeddings)


# ========================
# SAVE
# ========================
faiss.write_index(index, "index.faiss")

with open("metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False)

print(" Index built successfully!")