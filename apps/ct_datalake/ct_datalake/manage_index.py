import frappe
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

MODEL_NAME = "intfloat/multilingual-e5-base"
model = SentenceTransformer(MODEL_NAME)
BASE_PATH = os.path.dirname(__file__)

def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return "" if x == 0 else str(x)
    return str(x).strip()

def build_internal_index():
    print("Building Internal Index from DocType Candidate...")
    candidates = frappe.get_all("Candidate", filters={"source": "Internal"}, fields=["*"])
    print(f"Loaded {len(candidates)} internal candidates.")
    
    if not candidates:
        print("No internal candidates found.")
        return

    texts = []
    # Re-assign faiss_id sequentially and save
    for idx, item in enumerate(candidates):
        frappe.db.set_value("Candidate", item.name, "faiss_id", idx, update_modified=False)
        item.faiss_id = idx
        
        text = f"""
        Tên: {safe_str(item.candidate_name)}
        Trường: {safe_str(item.affiliation)}
        Học hàm: {safe_str(item.hoc_ham)}
        Học vị: {safe_str(item.hoc_vi)}
        Chức vụ: {safe_str(item.chuc_vu)}
        Lĩnh vực: {safe_str(item.san_pham_thuc_hien)}
        """
        text = "passage: " + text.strip()
        texts.append(text)
        
    frappe.db.commit()
    
    print("Encoding internal embeddings...")
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    
    index_file = os.path.join(BASE_PATH, "index.faiss")
    faiss.write_index(index, index_file)
    print(f"Internal index built successfully: {index_file}")

def build_external_index():
    print("Building External Index from DocType Candidate...")
    candidates = frappe.get_all("Candidate", filters={"source": "External"}, fields=["*"])
    print(f"Loaded {len(candidates)} external candidates.")
    
    if not candidates:
        print("No external candidates found.")
        return

    texts = []
    for idx, item in enumerate(candidates):
        frappe.db.set_value("Candidate", item.name, "faiss_id", idx, update_modified=False)
        item.faiss_id = idx
        
        text = f"""
        Name: {safe_str(item.candidate_name)}
        University: {safe_str(item.affiliation)}
        City: {safe_str(item.city)}
        Affiliation: {safe_str(item.affiliation)}
        Research Interests: {safe_str(item.interests)}
        Citations: {safe_str(item.citations)}
        H-index: {safe_str(item.h_index)}
        """
        text = "passage: " + text.strip()
        texts.append(text)
        
    frappe.db.commit()
    
    print("Encoding external embeddings...")
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)
    embeddings = np.array(embeddings).astype("float32")
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    
    index_file = os.path.join(BASE_PATH, "index_out.faiss")
    faiss.write_index(index, index_file)
    print(f"External index built successfully: {index_file}")

def run():
    build_internal_index()
    build_external_index()

if __name__ == "__main__":
    pass
