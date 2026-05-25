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

    return hashlib.md5(raw.encode()).hexdigest()


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
8. Format rõ ràng, dễ đọc.

Format mẫu:

# 1. Tên ứng viên
- Match Score: 92/100
- Đánh giá tổng quan:
- Điểm mạnh:
- Điểm cần khai thác sâu:
- Câu hỏi phỏng vấn gợi ý:
- Rủi ro / thiếu sót:

Trả lời:
"""


# ========================
# RERANK
# ========================
def rerank(
    query,
    candidates,
    mode="in"
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
        return "⚠️ Chưa cấu hình OPENAI_API_KEY. Vui lòng thiết lập biến môi trường."

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
                        "headhunter và cố vấn phỏng vấn cấp cao."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        result = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        if not result:
            result = "⚠️ OpenAI không trả kết quả"

        # ========================
        # SAVE CACHE
        # ========================
        CACHE[key] = result

        save_cache()

        return result

    except Exception as e:

        return f"❌ Lỗi OpenAI API: {str(e)}"