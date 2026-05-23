import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
gpt_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def create_draft(
    candidate_info: str,
    doc_type: str = "invite_collab",
    org_name: str = "",
    sender_name: str = "",
    extra_note: str = "",
) -> dict:
    if not gpt_client:
        return {"error": "OPENAI_API_KEY chưa được cấu hình"}

    DRAFT_PROMPTS = {
        "invite_collab":   "Thư mời hợp tác nghiên cứu khoa học",
        "invite_expert":   "Thư mời tham gia hội đồng chuyên gia phản biện",
        "invite_project":  "Thư mời tham gia dự án nghiên cứu",
        "invite_lecture":  "Thư mời giảng dạy hoặc báo cáo chuyên đề",
        "consult_request": "Công văn đề nghị tư vấn chuyên môn",
        "partnership":     "Thư đề xuất hợp tác chiến lược dài hạn",
    }

    doc_label = DRAFT_PROMPTS.get(doc_type, "Thư mời hợp tác")
    org = org_name or "đơn vị chúng tôi"
    sender_line = f"Người ký: {sender_name}" if sender_name else ""
    extra_line = f"Lưu ý thêm: {extra_note}" if extra_note else ""

    prompt = f"""Bạn là chuyên viên soạn thảo văn bản hành chính - ngoại giao chuyên nghiệp.
Hãy soạn một "{doc_label}" bằng tiếng Việt, trang trọng, chuyên nghiệp và đầy đủ.

Thông tin ứng viên/chuyên gia cần mời:
{candidate_info}

Đơn vị gửi: {org}
{sender_line}
{extra_line}

Yêu cầu:
- Văn phong lịch sự, trang trọng, đúng phong cách văn bản hành chính Việt Nam
- Đề cập cụ thể đến lĩnh vực chuyên môn của ứng viên
- Có đầy đủ: Kính gửi, Nội dung chính, Lời kết, Ký tên
- Độ dài phù hợp (khoảng 200-350 từ)
- Để trống [ngày tháng], [địa điểm], [số điện thoại liên hệ] nếu chưa có thông tin"""

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        draft_text = response.choices[0].message.content
    except Exception as e:
        return {"error": f"GPT error: {str(e)}"}

    return {
        "doc_type": doc_type,
        "doc_label": doc_label,
        "draft": draft_text,
    }

if __name__ == "__main__":
    # Test script khi chạy trực tiếp file
    import sys
    print("Testing draft_doc.py...")
    result = create_draft(
        candidate_info='{"name": "Nguyễn Văn A", "expertise": "Trí tuệ nhân tạo, Xử lý ngôn ngữ tự nhiên", "school": "Đại học Bách Khoa"}',
        doc_type="invite_collab",
        org_name="Viện Công Nghệ AI",
        sender_name="Giám đốc Trần B"
    )
    if "error" in result:
        print("Lỗi:", result["error"])
    else:
        print("\n--- KẾT QUẢ SOẠN THẢO ---\n")
        print(result["draft"])
        print("\n--------------------------\n")
