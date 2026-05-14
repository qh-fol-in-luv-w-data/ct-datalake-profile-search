import frappe
import json
import os

def import_candidates():
    app_path = frappe.get_app_path("ct_datalake")
    
    # 1. Import Internal Candidates
    internal_file = os.path.join(app_path, "ct_datalake", "danh_sach_giao_su_tien_si_chuyen_gia_v5.json")
    if os.path.exists(internal_file):
        print(f"Importing Internal from {internal_file}...")
        with open(internal_file, "r", encoding="utf-8") as f:
            data_in = json.load(f)
            
        for i, row in enumerate(data_in):
            try:
                # Tránh trùng lặp, nhưng nếu tên trùng thì sao? Tốt nhất là xoá hết Candidate cũ trước khi import (hoặc dùng name/id)
                # Để an toàn, chúng ta cứ tạo mới. Bạn có thể truncate table Candidate trước khi chạy nếu cần.
                doc = frappe.new_doc("Candidate")
                doc.candidate_name = row.get("trường họ và tên", "Unknown")
                doc.source = "Internal"
                doc.affiliation = row.get("trường", "")
                doc.hoc_ham = str(row.get("học hàm", ""))
                doc.hoc_vi = str(row.get("học vị", ""))
                doc.chuc_vu = str(row.get("chức vụ", ""))
                doc.san_pham_thuc_hien = str(row.get("sản phẩm thực hiện", ""))
                doc.faiss_id = i
                doc.insert(ignore_permissions=True)
            except Exception as e:
                print(f"Error inserting internal candidate at index {i}: {str(e)}")
        
        frappe.db.commit()
        print(f"Imported {len(data_in)} internal candidates.")
    else:
        print("Internal data file not found.")

    # 2. Import External Candidates
    external_file = os.path.join(app_path, "ct_datalake", "data_out_translated.json")
    if os.path.exists(external_file):
        print(f"Importing External from {external_file}...")
        with open(external_file, "r", encoding="utf-8") as f:
            data_out = json.load(f)
            
        for i, row in enumerate(data_out):
            try:
                doc = frappe.new_doc("Candidate")
                doc.candidate_name = row.get("name", "Unknown")
                doc.source = "External"
                doc.affiliation = row.get("affiliation", "")
                doc.email = row.get("email", "")
                
                interests = row.get("interests", [])
                if isinstance(interests, list):
                    doc.interests = ", ".join(interests)
                else:
                    doc.interests = str(interests)
                
                # Safe parse int
                try:
                    c = str(row.get("citations", "0")).replace(",", "")
                    doc.citations = int(c) if c.isdigit() else 0
                except:
                    doc.citations = 0
                
                try:
                    h = str(row.get("h_index", "0"))
                    doc.h_index = int(h) if h.isdigit() else 0
                except:
                    doc.h_index = 0
                    
                doc.scholar_url = row.get("url", "")
                doc.city = row.get("city", "")
                doc.faiss_id = i
                doc.insert(ignore_permissions=True)
            except Exception as e:
                print(f"Error inserting external candidate at index {i}: {str(e)}")
        
        frappe.db.commit()
        print(f"Imported {len(data_out)} external candidates.")
    else:
        print("External data file not found.")

def run():
    # Xoá data cũ để tránh duplicate nếu chạy nhiều lần
    frappe.db.sql("DELETE FROM `tabCandidate`")
    frappe.db.commit()
    print("Cleared existing Candidates.")
    
    import_candidates()

if __name__ == "__main__":
    pass
