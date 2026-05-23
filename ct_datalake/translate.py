import json
import time
from deep_translator import GoogleTranslator

def translate_interests(input_file, output_file):
    # Đọc file JSON gốc
    print(" đang đọc file dữ liệu...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {input_file} trong thư mục này.")
        return

    # Khởi tạo bộ dịch (Anh -> Việt)
    translator = GoogleTranslator(source='en', target='vi')

    total = len(data)
    print(f" Bắt đầu dịch {total} chuyên gia. Vui lòng chờ...")

    for i, entry in enumerate(data):
        if 'interests' in entry and entry['interests']:
            translated_list = []
            for item in entry['interests']:
                if not item.strip():
                    continue
                try:
                    # Dịch từng cụm từ trong interests
                    translated = translator.translate(item)
                    translated_list.append(translated)
                    # Tránh bị Google block do request quá nhanh
                    time.sleep(0.1) 
                except Exception as e:
                    print(f"\n[!] Lỗi khi dịch '{item}': {e}")
                    translated_list.append(item) # Giữ nguyên nếu lỗi
            
            entry['interests'] = translated_list

        # In tiến độ chạy trên terminal
        if (i + 1) % 5 == 0 or i + 1 == total:
            print(f"\r Tiến độ: {i+1}/{total} ({(i+1)/total*100:.1f}%)", end="", flush=True)

    # Lưu file mới
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n Hoàn thành! File đã được lưu tại: {output_file}")

if __name__ == "__main__":
    # Thay đổi tên file đầu vào của bạn ở đây
    translate_interests('data_out_filter.json', 'data_out_translated.json')