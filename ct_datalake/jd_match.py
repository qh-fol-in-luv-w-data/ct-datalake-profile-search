"""
jd_match.py – Job Description → Candidate Matching
====================================================
Hỗ trợ đầu vào JD:
  - Text nhập tay
  - Upload file .txt / .md
  - Upload file .pdf
  - Upload file .docx
"""

import io
import json
import os
from typing import Literal

from openai import OpenAI
from .openai_key import get_openai_client

from .search import search

# ========================
# CONFIG
# ========================
OPENAI_MODEL = "gpt-4o-mini"


# ========================
# FIELD MAPPINGS
# ========================

IN_FIELDS = {
    "name": [
        "trường họ và tên",
        "họ và tên",
        "tên",
        "name",
        "full_name",
    ],

    "school": [
        "trường",
        "school",
        "university",
    ],

    "title": [
        "học hàm",
        "học vị",
        "title",
        "degree",
    ],

    "academic_rank": [
        "học hàm",
    ],

    "degree": [
        "học vị",
    ],

    "position": [
        "chức vụ",
        "position",
        "role",
    ],

    "expertise": [
        "sản phẩm thực hiện",
        "chuyên môn",
        "chuyên ngành",
        "lĩnh vực",
        "expertise",
        "specialization",
    ],
}

OUT_FIELDS = {
    "name": [
        "name",
        "author",
        "full_name",
    ],

    "affiliation": [
        "affiliation",
        "organization",
        "institution",
    ],

    "email": [
        "email",
        "verified_email",
    ],

    "interests": [
        "interests",
        "research_interests",
        "topics",
    ],

    "citations": [
        "citations",
        "citation_count",
    ],

    "h_index": [
        "h_index",
        "hindex",
    ],

    "url": [
        "url",
        "profile_url",
        "scholar_url",
    ],

    "university_abbr": [
        "university_abbr",
    ],

    "university_name": [
        "university_name",
    ],

    "city": [
        "city",
    ],
}


def _pick(data: dict, keys: list[str], default=""):
    for k in keys:
        v = data.get(k)

        if v is None:
            continue

        if isinstance(v, str) and not v.strip():
            continue

        return v

    return default


def normalize_candidate(data: dict, mode: str) -> dict:
    fields = IN_FIELDS if mode == "in" else OUT_FIELDS

    return {
        "name": _pick(data, fields.get("name", [])),

        "school": _pick(data, fields.get("school", [])),

        "title": _pick(data, fields.get("title", [])),

        "academic_rank": _pick(data, fields.get("academic_rank", [])),

        "degree": _pick(data, fields.get("degree", [])),

        "position": _pick(data, fields.get("position", [])),

        "expertise": _pick(data, fields.get("expertise", [])),

        # OUT
        "affiliation": _pick(data, fields.get("affiliation", [])),

        "email": _pick(data, fields.get("email", [])),

        "interests": _pick(data, fields.get("interests", []), []),

        "citations": _pick(data, fields.get("citations", [])),

        "h_index": _pick(data, fields.get("h_index", [])),

        "url": _pick(data, fields.get("url", [])),

        "university_abbr": _pick(data, fields.get("university_abbr", [])),

        "university_name": _pick(data, fields.get("university_name", [])),

        "city": _pick(data, fields.get("city", [])),
    }


# ========================
# FILE READERS
# ========================
def _read_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def _read_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Cần cài pypdf: pip install pypdf")

    reader = PdfReader(io.BytesIO(file_bytes))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())

    return "\n\n".join(p for p in pages if p)


def _read_docx(file_bytes: bytes) -> str:
    try:
        import docx
    except ImportError:
        raise ImportError("Cần cài python-docx: pip install python-docx")

    doc = docx.Document(io.BytesIO(file_bytes))

    return "\n".join(
        p.text for p in doc.paragraphs if p.text.strip()
    )


def extract_text_from_upload(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith((".txt", ".md")):
        return _read_txt(data)

    elif name.endswith(".pdf"):
        return _read_pdf(data)

    elif name.endswith(".docx"):
        return _read_docx(data)

    else:
        ext = os.path.splitext(name)[1] or "(không rõ)"

        raise ValueError(
            f"Định dạng '{ext}' chưa được hỗ trợ. "
            "Vui lòng dùng .txt, .md, .pdf, hoặc .docx."
        )


# ========================
# STEP 1 – PARSE JD
# ========================
def parse_jd(jd_text: str, session_info=None) -> dict:
    system_prompt = """
Bạn là chuyên gia HR và tuyển dụng.

Nhiệm vụ:
Phân tích Job Description (JD) và trả về JSON:

{
  "keywords": [],
  "required_skills": [],
  "nice_to_have": [],
  "level": "fresher|mid|senior|expert",
  "domain": "string",
  "summary": "string"
}

Trả về JSON thuần.
"""

    if not get_openai_client():
        return {
            "keywords": [],
            "summary": jd_text[:200]
        }

    response = get_openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"JD:\n{jd_text}"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    if session_info and session_info[0]:
        session_name, action_name = session_info
        from ct_datalake.utils.activity_logger import ActivityLogger
        _log = ActivityLogger(prefix="DL", module="CT DataLake")
        if hasattr(response, "usage") and response.usage:
            _log.log_ai_call(
                session_name=session_name,
                action_name=action_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

    raw = response.choices[0].message.content or "{}"

    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        return {
            "keywords": [],
            "summary": jd_text[:200]
        }


# ========================
# STEP 2 – RETRIEVE
# ========================
def _retrieve_candidates(
    parsed: dict,
    mode: Literal["in", "out"],
    top_k: int = 10,
) -> list[dict]:

    keywords = parsed.get("keywords", [])
    domain = parsed.get("domain", "")
    summary = parsed.get("summary", "")

    queries = list(dict.fromkeys(filter(None, [
        summary,
        domain,
        " ".join(keywords[:5]),
        *keywords,
    ])))

    seen_keys = set()
    merged = []

    for q in queries:

        if not q.strip():
            continue

        hits = search(
            query=q,
            mode=mode,
            top_k=top_k
        )

        for hit in hits:

            d = hit["data"]

            norm = normalize_candidate(d, mode)

            key = (
                norm.get("url")
                or d.get("id")
                or f"{norm.get('name','')}{norm.get('school','')}"
            )

            if key and key not in seen_keys:
                seen_keys.add(key)
                merged.append(hit)

    merged.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return merged[: top_k * 3]


# ========================
# STEP 3 – RERANK
# ========================
def _rerank_candidates(
    jd_text: str,
    parsed_jd: dict,
    candidates: list[dict],
    mode: str,
    top_k: int = 5,
    session_info=None,
) -> list[dict]:

    if not candidates:
        return []

    slim = []

    for i, c in enumerate(candidates):

        d = c["data"]

        norm = normalize_candidate(d, mode)

        slim.append({
            "index": i,

            "faiss_score": round(c["score"], 4),

            "name": norm["name"],

            "school": norm["school"],

            "title": norm["title"],

            "academic_rank": norm["academic_rank"],

            "degree": norm["degree"],

            "position": norm["position"],

            "expertise": str(norm["expertise"])[:1200],

            # OUT
            "affiliation": norm["affiliation"],

            "email": norm["email"],

            "interests": norm["interests"],

            "citations": norm["citations"],

            "h_index": norm["h_index"],

            "url": norm["url"],

            "university_name": norm["university_name"],

            "city": norm["city"],
        })

    system_prompt = """
Bạn là chuyên gia tuyển dụng cấp cao.

Đánh giá mức độ phù hợp của từng ứng viên với Job Description.
LƯU Ý QUAN TRỌNG: Tất cả các nội dung phân tích (strengths, gaps, reason) BẮT BUỘC phải viết hoàn toàn bằng Tiếng Việt.

Thang điểm:
90-100 = excellent
70-89 = good
50-69 = fair
0-49 = poor

Trả về JSON:

{
  "ranked": [
    {
      "index": 0,
      "match_score": 95,
      "verdict": "excellent",
      "strengths": ["Điểm mạnh 1 bằng tiếng Việt", "Điểm mạnh 2"],
      "gaps": ["Thiếu sót 1 bằng tiếng Việt", "Thiếu sót 2"],
      "reason": "Giải thích chi tiết bằng Tiếng Việt vì sao chọn điểm này"
    }
  ]
}
"""

    if not get_openai_client():
        return candidates[:top_k]

    user_content = (
        f"=== JOB DESCRIPTION ===\n{jd_text}\n\n"
        f"=== PARSED JD ===\n"
        f"{json.dumps(parsed_jd, ensure_ascii=False)}\n\n"
        f"=== CANDIDATES ===\n"
        f"{json.dumps(slim, ensure_ascii=False, indent=2)}"
    )

    response = get_openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    if session_info and session_info[0]:
        session_name, action_name = session_info
        from ct_datalake.utils.activity_logger import ActivityLogger
        _log = ActivityLogger(prefix="DL", module="CT DataLake")
        if hasattr(response, "usage") and response.usage:
            _log.log_ai_call(
                session_name=session_name,
                action_name=action_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

    raw = response.choices[0].message.content or "{}"

    try:
        result = json.loads(raw)

    except json.JSONDecodeError:
        return candidates[:top_k]

    output = []

    ranked = sorted(
        result.get("ranked", []),
        key=lambda x: x.get("match_score", 0),
        reverse=True
    )

    for rm in ranked:

        idx = rm.get("index")

        if idx is None or idx >= len(candidates):
            continue

        output.append({
            **candidates[idx],

            "match_score": rm.get("match_score", 0),

            "verdict": rm.get("verdict", ""),

            "strengths": rm.get("strengths", []),

            "gaps": rm.get("gaps", []),

            "reason": rm.get("reason", ""),
        })

        if len(output) >= top_k:
            break

    return output



def _rerank_g600_candidates(
    g600_domain: str,
    keywords: list,
    candidates: list[dict],
    top_k: int = 5,
    session_info=None,
) -> list[dict]:

    if not candidates:
        return []

    slim = []
    for i, c in enumerate(candidates):
        d = c["data"]
        cand_mode = c.get("mode", "in")
        norm = normalize_candidate(d, cand_mode)
        slim.append({
            "index": i,
            "name": norm["name"],
            "school": norm["school"],
            "title": norm["title"],
            "academic_rank": norm["academic_rank"],
            "degree": norm["degree"],
            "position": norm["position"],
            "expertise": str(norm["expertise"])[:1200],
            "affiliation": norm["affiliation"],
            "email": norm["email"],
            "interests": norm["interests"],
            "citations": norm["citations"],
            "h_index": norm["h_index"],
            "url": norm["url"],
            "university_name": norm["university_name"],
            "city": norm["city"],
        })

    system_prompt = '''
Bạn là một chuyên gia đánh giá và tìm kiếm nhân tài / chuyên gia khoa học cấp cao.

Hãy đánh giá mức độ phù hợp chuyên môn của từng chuyên gia/ứng viên đối với Lĩnh vực nghiên cứu/dự án được đề cập trong Tờ trình G600.

LƯU Ý ĐẶC BIỆT QUAN TRỌNG:
1. Chuyên môn của chuyên gia chủ yếu nằm ở mảng "interests" (các hướng nghiên cứu). BẠN BẮT BUỘC phải đọc mảng "interests" này để đối chiếu. Tuyệt đối KHÔNG ĐƯỢC kết luận là "không có thông tin" nếu mảng "interests" hoặc "expertise" có dữ liệu.
2. Phải đánh giá ngữ nghĩa rộng: VD Tờ trình cần "Công nghệ thông tin" thì các chuyên gia có interests "Trí tuệ nhân tạo", "Học máy", "Xử lý ngôn ngữ tự nhiên" ĐỀU LÀ KHỚP và phải được điểm cao. Không được bắt bẻ câu chữ cứng nhắc.
3. BẮT BUỘC phải đánh giá và trả về kết quả cho TẤT CẢ các chuyên gia trong danh sách đầu vào vào mảng `ranked`, tuyệt đối không được bỏ sót bất kỳ ai, kể cả khi điểm của họ là 0.

Thang điểm chuyên môn (0-100):
90-100 = Rất xuất sắc (Khớp hoàn toàn chuyên môn sâu)
70-89 = Tốt (Có nghiên cứu/kinh nghiệm liên quan)
50-69 = Khá (Có kỹ năng/quan tâm nhưng chưa sâu)
0-49 = Kém (Không phù hợp)

Trả về JSON:
{
  "ranked": [
    {
      "index": 0,
      "match_score": 95,
      "verdict": "excellent",
      "strengths": ["Các điểm chuyên môn/nghiên cứu của chuyên gia KHỚP với yêu cầu của Tờ trình G600"],
      "gaps": ["Những chuyên môn/yêu cầu mà Tờ trình G600 CẦN nhưng chuyên gia này đang THIẾU"],
      "reason": "Giải thích ngắn gọn lý do tại sao chấm điểm này dựa trên việc đối chiếu chuyên gia với Tờ trình G600"
    }
  ]
}
'''

    if not get_openai_client():
        return candidates[:top_k]

    user_content = (
        f"=== YÊU CẦU TỪ TỜ TRÌNH G600 ===\nLĩnh vực: {g600_domain}\nTừ khoá: {', '.join(keywords)}\n\n"
        f"=== DANH SÁCH CHUYÊN GIA ===\n"
        f"{json.dumps(slim, ensure_ascii=False, indent=2)}"
    )

    response = get_openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    if session_info and session_info[0]:
        session_name, action_name = session_info
        from ct_datalake.utils.activity_logger import ActivityLogger
        _log = ActivityLogger(prefix="DL", module="CT DataLake")
        if hasattr(response, "usage") and response.usage:
            _log.log_ai_call(
                session_name=session_name,
                action_name=action_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

    raw = response.choices[0].message.content or "{}"
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return candidates[:top_k]

    output = []
    ranked = sorted(
        result.get("ranked", []),
        key=lambda x: x.get("match_score", 0),
        reverse=True
    )

    for rm in ranked:
        idx = rm.get("index")
        if idx is None or idx >= len(candidates):
            continue
        output.append({
            **candidates[idx],
            "match_score": rm.get("match_score", 0),
            "verdict": rm.get("verdict", ""),
            "strengths": rm.get("strengths", []),
            "gaps": rm.get("gaps", []),
            "reason": rm.get("reason", ""),
        })
        if len(output) >= top_k:
            break

    return output
# ========================
# PUBLIC API
# ========================
def match_jd(
    jd_text: str,
    mode: Literal["in", "out"] = "in",
    top_k: int = 5,
    fast: bool = False,
    session_info=None,
) -> dict:

    parsed = parse_jd(jd_text, session_info=session_info)

    raw_candidates = _retrieve_candidates(
        parsed,
        mode=mode,
        top_k=top_k
    )

    total_found = len(raw_candidates)

    if fast or not raw_candidates:
        return {
            "parsed_jd": parsed,
            "candidates": raw_candidates[:top_k],
            "total_found": total_found
        }

    ranked = _rerank_candidates(
        jd_text=jd_text,
        parsed_jd=parsed,
        candidates=raw_candidates,
        mode=mode,
        top_k=top_k,
        session_info=session_info
    )

    return {
        "parsed_jd": parsed,
        "candidates": ranked,
        "total_found": total_found
    }


# ========================
# STREAMLIT UI
# ========================
def render_jd_uploader():
    import streamlit as st

    tab_file, tab_text = st.tabs([
        "📎 Upload file",
        "✏️ Nhập text"
    ])

    jd_text = None

    with tab_file:

        uploaded = st.file_uploader(
            "Chọn file JD",
            type=["txt", "md", "pdf", "docx"]
        )

        if uploaded is not None:

            try:
                jd_text = extract_text_from_upload(uploaded)

                st.success(
                    f"✅ Đã đọc {uploaded.name}"
                )

            except Exception as e:
                st.error(str(e))

    with tab_text:

        typed = st.text_area(
            "Dán JD vào đây",
            height=280
        )

        if typed.strip():
            jd_text = typed.strip()

    return jd_text


def render_match_results(results: dict, mode: str):
    import streamlit as st

    parsed = results.get("parsed_jd", {})
    cands = results.get("candidates", [])
    total = results.get("total_found", 0)

    st.caption(
        f"🔎 Tìm thấy {total} ứng viên"
    )

    if not cands:
        st.warning("Không tìm thấy ứng viên.")
        return

    ICON = {
        "excellent": "🟢",
        "good": "🔵",
        "fair": "🟡",
        "poor": "🔴"
    }

    for i, c in enumerate(cands, 1):

        raw = c["data"]

        d = normalize_candidate(raw, mode)

        score = c.get(
            "match_score",
            c.get("score", 0)
        )

        verdict = c.get("verdict", "")

        name = d["name"] or "Ẩn danh"

        with st.expander(
            f"{ICON.get(verdict,'⚪')} #{i} "
            f"{name} — Match: {score}/100",
            expanded=(i == 1),
        ):

            col_l, col_r = st.columns([3, 2])

            with col_l:

                if mode == "in":

                    if d["school"]:
                        st.markdown(
                            f"**Trường:** {d['school']}"
                        )

                    if d["academic_rank"] or d["degree"]:
                        st.markdown(
                            f"**Học hàm/vị:** "
                            f"{d['academic_rank']} "
                            f"{d['degree']}"
                        )

                    if d["position"]:
                        st.markdown(
                            f"**Chức vụ:** {d['position']}"
                        )

                    if d["expertise"]:
                        st.markdown(
                            f"**Mô tả nghiên cứu/sản phẩm:** "
                            f"{d['expertise']}"
                        )

                else:

                    if d["affiliation"]:
                        st.markdown(
                            f"**Affiliation:** "
                            f"{d['affiliation']}"
                        )

                    if d["university_name"]:
                        st.markdown(
                            f"**University:** "
                            f"{d['university_name']} "
                            f"({d['university_abbr']})"
                        )

                    if d["city"]:
                        st.markdown(
                            f"**City:** {d['city']}"
                        )

                    if d["email"]:
                        st.markdown(
                            f"**Email:** {d['email']}"
                        )

                    if d["interests"]:
                        st.markdown(
                            f"**Interests:** "
                            f"{', '.join(d['interests'])}"
                        )

                    st.markdown(
                        f"**Citations:** "
                        f"{d['citations']} "
                        f"| h-index: {d['h_index']}"
                    )

                    if d["url"]:
                        st.markdown(
                            f"**URL:** "
                            f"[{d['url']}]({d['url']})"
                        )

            with col_r:

                if c.get("reason"):
                    st.info(f"💬 {c['reason']}")

                if c.get("strengths"):

                    st.markdown("**✅ Điểm mạnh:**")

                    for s in c["strengths"]:
                        st.markdown(f"- {s}")

                if c.get("gaps"):

                    st.markdown("**⚠️ Còn thiếu:**")

                    for g in c["gaps"]:
                        st.markdown(f"- {g}")


