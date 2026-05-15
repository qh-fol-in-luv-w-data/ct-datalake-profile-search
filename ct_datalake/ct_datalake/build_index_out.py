import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ========================
# CONFIG
# ========================
MODEL_NAME = "intfloat/multilingual-e5-base"
INPUT_FILE = "data_out_translated.json"
INDEX_FILE = "index_out.faiss"
META_FILE = "metadata_out.json"

model = SentenceTransformer(MODEL_NAME)


# ========================
# UTILS
# ========================
def safe_str(x):
    if x is None:
        return ""
    return str(x).strip()


def safe_int(x):
    try:
        return int(str(x).replace(",", "").strip())
    except:
        return 0


def normalize_text(x):
    return safe_str(x).lower()


# ========================
# LOAD DATA
# ========================
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"📦 Loaded {len(data)} records")


# ========================
# DEDUPE
# duplicate theo:
# name + affiliation + url
# ========================
seen = set()
clean_data = []

for item in data:
    key = (
        normalize_text(item.get("name")),
        normalize_text(item.get("affiliation")),
        normalize_text(item.get("url")),
    )

    if key not in seen:
        seen.add(key)
        clean_data.append(item)

data = clean_data
print(f"✅ After dedupe: {len(data)} records")


# ========================
# BUILD TEXT FOR EMBEDDING
# ========================
texts = []
metadata = []

for item in data:
    interests = item.get("interests", [])
    if isinstance(interests, list):
        interests = ", ".join(interests)
    else:
        interests = safe_str(interests)

    text = f"""
    Name: {safe_str(item.get("name"))}
    University: {safe_str(item.get("university_name"))}
    University Abbr: {safe_str(item.get("university_abbr"))}
    City: {safe_str(item.get("city"))}
    Affiliation: {safe_str(item.get("affiliation"))}
    Research Interests: {interests}
    Citations: {safe_str(item.get("citations"))}
    H-index: {safe_str(item.get("h_index"))}
    """

    # E5 format
    text = "passage: " + text.strip()

    texts.append(text)
    metadata.append(item)


# ========================
# ENCODE
# ========================
print("🧠 Encoding embeddings...")

embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=True,
    batch_size=32
)

embeddings = np.array(embeddings).astype("float32")


# ========================
# BUILD FAISS INDEX
# cosine similarity
# ========================
dim = embeddings.shape[1]

index = faiss.IndexFlatIP(dim)
index.add(embeddings)

print(f"📌 Index size: {index.ntotal}")


# ========================
# SAVE
# ========================
faiss.write_index(index, INDEX_FILE)

with open(META_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print("✅ Saved:")
print(f" - {INDEX_FILE}")
print(f" - {META_FILE}")
print("🚀 Build index completed!")