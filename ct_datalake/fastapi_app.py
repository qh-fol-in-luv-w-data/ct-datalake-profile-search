from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import json
from typing import Optional
from dotenv import load_dotenv

# Load .env từ thư mục gốc project
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from .search import search as faiss_search
from .llm_rerank import rerank
from .jd_match import (
    match_jd,
    normalize_candidate,
    parse_jd,
    extract_text_from_upload as _extract_text,
)
from .ai_matching import extract_keywords, load_datasets, search_domain
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from . import ai_matching as _rc
from .draft_doc import create_draft

app = FastAPI(title="AI Candidate Search API (Local)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_api_key = os.getenv("OPENAI_API_KEY", "").strip()
gpt_client = OpenAI(api_key=_api_key) if _api_key else None

_embed_model = None
_datasets = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
    return _embed_model

def get_datasets():
    global _datasets
    if _datasets is None:
        _datasets = load_datasets()
    return _datasets

@app.get("/api/method/ct_datalake.ct_datalake.api.root")
def root():
    return {"message": {"status": "ok"}}

@app.post("/api/method/ct_datalake.ct_datalake.api.semantic_search")
@app.get("/api/method/ct_datalake.ct_datalake.api.semantic_search")
def semantic_search(query: str, mode: str = "in", top_k: int = 5):
    raw = faiss_search(query=query, mode=mode, top_k=top_k)
    results = []
    for r in raw:
        norm = normalize_candidate(r["data"], mode)
        results.append({
            "faiss_score": round(r["score"], 4),
            "candidate": norm,
            "raw": r["data"],
        })
    return {"message": {"query": query, "mode": mode, "total": len(results), "results": results}}

@app.post("/api/method/ct_datalake.ct_datalake.api.semantic_search_llm")
@app.get("/api/method/ct_datalake.ct_datalake.api.semantic_search_llm")
def semantic_search_llm(query: str, mode: str = "in", top_k: int = 5):
    raw = faiss_search(query=query, mode=mode, top_k=max(top_k * 2, 10))
    if not raw:
        return {"message": {"query": query, "mode": mode, "total_found": 0, "llm_analysis": ""}}
    analysis = rerank(query=query, candidates=raw[:top_k], mode=mode)
    return {"message": {"query": query, "mode": mode, "total_found": len(raw), "candidates_sent_to_llm": top_k, "llm_analysis": analysis}}

@app.post("/api/method/ct_datalake.ct_datalake.api.jd_match")
@app.get("/api/method/ct_datalake.ct_datalake.api.jd_match")
def jd_match_api(jd_text: str, mode: str = "in", top_k: int = 5, fast: str = "false"):
    fast_bool = fast.lower() == "true"
    result = match_jd(jd_text=jd_text, mode=mode, top_k=top_k, fast=fast_bool)
    return {"message": result}

class MockUpload:
    def __init__(self, name, data):
        self.name = name
        self._data = data
    def read(self):
        return self._data

@app.post("/api/method/ct_datalake.ct_datalake.api.jd_match_upload")
async def jd_match_upload(file: UploadFile = File(...), mode: str = Form("in"), top_k: int = Form(5), fast: str = Form("false")):
    content = await file.read()
    fast_bool = fast.lower() == "true"
    jd_text = _extract_text(MockUpload(file.filename, content))
    result = match_jd(jd_text=jd_text, mode=mode, top_k=top_k, fast=fast_bool)
    return {"message": result}

@app.post("/api/method/ct_datalake.ct_datalake.api.g600_analyze")
async def g600_analyze(file: UploadFile = File(...), source: str = Form("both"), top_k: int = Form(5), score_threshold: float = Form(0.40)):
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    domains = extract_keywords(tmp_path, gpt_client)
    os.unlink(tmp_path)
    
    datasets = get_datasets()
    embed_model = get_embed_model()
    
    active = datasets
    if source == "in":
        active = {k: v for k, v in datasets.items() if k == "in"}
    elif source == "out":
        active = {k: v for k, v in datasets.items() if k == "out"}
        
    _rc.TOP_K = top_k
    _rc.SCORE_THRESHOLD = score_threshold
    
    domain_results = []
    for domain in domains:
        hits = search_domain(domain, active, embed_model)
        candidates = []
        for hit in hits:
            norm = normalize_candidate(hit["data"], hit["mode"])
            candidates.append({
                "source": "🌐 Google Scholar" if hit["mode"] == "out" else "🏫 Nội bộ",
                "faiss_score": hit["score"],
                "candidate": norm,
                "raw": hit["data"],
            })
        domain_results.append({
            "domain_name": domain["name"],
            "query_vi": domain.get("query_vi", ""),
            "query_en": domain.get("query_en", ""),
            "keywords_vi": domain.get("keywords_vi", []),
            "keywords_en": domain.get("keywords_en", []),
            "total_candidates": len(candidates),
            "candidates": candidates,
        })
    return {"message": {"source": source, "top_k_per_domain": top_k, "score_threshold": score_threshold, "total_domains": len(domain_results), "domains": domain_results}}

@app.post("/api/method/ct_datalake.ct_datalake.api.draft_document")
@app.get("/api/method/ct_datalake.ct_datalake.api.draft_document")
def draft_document(candidate_info: str, doc_type: str = "invite_collab", org_name: str = "", sender_name: str = "", extra_note: str = ""):
    result = create_draft(
        candidate_info=candidate_info,
        doc_type=doc_type,
        org_name=org_name,
        sender_name=sender_name,
        extra_note=extra_note,
    )
    if "error" in result:
        return {"message": {"error": result["error"]}}
    return {"message": result}
