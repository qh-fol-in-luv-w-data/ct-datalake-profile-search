# llm_rerank.py

import json
import hashlib
import os

from openai import OpenAI
from .openai_key import get_openai_client

# ========================
# CONFIG
# ========================
OPENAI_MODEL = "gpt-4o-mini"


BASE_PATH = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_PATH, "rerank_cache.json")
CACHE_VERSION = "v3"

# ========================
# LOAD CACHE
# ========================
if os.path.exists(CACHE_FILE):

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)

else:
    CACHE = {}


def save_cache():

    with open(CACHE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            CACHE,
            f,
            ensure_ascii=False,
            indent=2
        )


# ========================
# HASH KEY
# ========================
def make_cache_key(query, candidates, mode="in"):

    raw = json.dumps(
        {
            "v": CACHE_VERSION,
            "mode": mode,
            "query": query,
            "candidates": candidates
        },
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(raw.encode()).hexdigest()


# ========================
# BUILD PROMPT
# ========================
def build_prompt(query, candidates, mode):

    source_name = (
        "Dữ liệu nội bộ"
        if mode == "in"
        else "Dữ liệu bên ngoài"
    )

    return f"""
Bạn là hệ thống AI tuyển dụng và cố vấn phỏng vấn chuyên gia.

Nguồn dữ liệu:
{source_name}

Yêu cầu tuyển dụng / dự án:
{query}

Danh sách ứng viên:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Nhiệm vụ:

1. Chọn các ứng viên phù hợp nhất.
2. Chấm điểm phù hợp từ 0-100.
3. Phân tích:
   - Điểm mạnh
   - Điểm phù hợp với dự án
   - Kỹ năng/chuyên môn nổi bật
4. Đưa ra:
   - Những điểm hội đồng nên khai thác sâu khi phỏng vấn
   - Các câu hỏi gợi ý để đánh giá chuyên môn
5. Nếu ứng viên chưa phù hợp, nêu rõ lý do.
6. Sắp xếp từ phù hợp nhất xuống thấp hơn.
7. Trả lời bằng tiếng Việt.
8. Trả về đúng MỘT CẤU TRÚC JSON MẢNG (Array of JSON objects). Không được kèm theo bất kỳ văn bản nào khác.

Format JSON mẫu bắt buộc:
[
  {{
    "candidate_name": "Tên ứng viên",
    "match_score": 92,
    "overview": "Đánh giá tổng quan...",
    "strengths": "Điểm mạnh...",
    "deep_dive": "Điểm cần khai thác sâu...",
    "interview_questions": [
      "Câu hỏi 1",
      "Câu hỏi 2"
    ],
    "risks": "Rủi ro / thiếu sót..."
  }}
]

Trả lời (chỉ JSON):
"""


# ========================
# RERANK
# ========================
def rerank(
    query,
    candidates,
    mode="in",
    session_info=None
):

    candidates = candidates[:10]

    key = make_cache_key(
        query,
        candidates,
        mode
    )

    # ========================
    # CACHE HIT
    # ========================
    if key in CACHE:

        print("⚡ Cache hit")

        return CACHE[key]

    # ========================
    # CACHE MISS
    # ========================
    print("🚀 Calling OpenAI...")

    if not get_openai_client():
        return [{"error": "⚠️ Chưa cấu hình OPENAI_API_KEY. Vui lòng thiết lập biến môi trường."}]

    prompt = build_prompt(
        query,
        candidates,
        mode
    )

    try:

        response = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là chuyên gia tuyển dụng, "
                        "headhunter và cố vấn phỏng vấn cấp cao. Luôn trả về kết quả dưới dạng JSON hợp lệ."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
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

        result_str = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        if not result_str:
            result = [{"error": "⚠️ OpenAI không trả kết quả"}]
        else:
            try:
                # Bắt OpenAI trả JSON object nên ta có thể cần bọc nó vào 1 key
                # Nhưng prompt yêu cầu trả JSON array. Để đảm bảo an toàn với response_format={"type": "json_object"},
                # ta nên parse tuỳ biến.
                import re
                # Lọc lấy array từ chuỗi trả về
                match = re.search(r'\[.*\]', result_str, re.DOTALL)
                if match:
                    result = json.loads(match.group(0))
                else:
                    result = json.loads(result_str)
                    
                if isinstance(result, dict) and "candidates" in result:
                    result = result["candidates"]
                elif isinstance(result, dict):
                    result = [result] # Fallback
            except json.JSONDecodeError:
                result = [{"error": "Lỗi parse JSON", "raw_content": result_str}]

        # ========================
        # SAVE CACHE
        # ========================
        CACHE[key] = result

        save_cache()

        return result

    except Exception as e:

        return [{"error": f"❌ Lỗi OpenAI API: {str(e)}"}]