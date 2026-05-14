import frappe

def create_candidate_doctype():
    if frappe.db.exists("DocType", "Candidate"):
        frappe.delete_doc("DocType", "Candidate", force=1)
        frappe.db.commit()
        try:
            frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabCandidate`")
        except:
            pass
        print("Deleted old DocType Candidate.")

    doc = frappe.get_doc({
        "doctype": "DocType",
        "module": "CT DataLake",
        "custom": 1,
        "name": "Candidate",
        "fields": [
            {"fieldname": "candidate_name", "fieldtype": "Data", "label": "Candidate Name", "reqd": 1, "in_list_view": 1},
            {"fieldname": "source", "fieldtype": "Select", "label": "Source", "options": "Internal\nExternal", "reqd": 1, "in_list_view": 1},
            {"fieldname": "affiliation", "fieldtype": "Small Text", "label": "Affiliation", "in_list_view": 1},
            {"fieldname": "email", "fieldtype": "Data", "label": "Email"},
            {"fieldname": "hoc_ham", "fieldtype": "Data", "label": "Học Hàm (Internal)"},
            {"fieldname": "hoc_vi", "fieldtype": "Data", "label": "Học Vị (Internal)"},
            {"fieldname": "chuc_vu", "fieldtype": "Small Text", "label": "Chức Vụ (Internal)"},
            {"fieldname": "san_pham_thuc_hien", "fieldtype": "Text", "label": "Sản phẩm thực hiện (Internal)"},
            {"fieldname": "interests", "fieldtype": "Text", "label": "Interests (External)"},
            {"fieldname": "citations", "fieldtype": "Int", "label": "Citations (External)"},
            {"fieldname": "h_index", "fieldtype": "Int", "label": "H-Index (External)"},
            {"fieldname": "scholar_url", "fieldtype": "Small Text", "label": "Scholar URL (External)"},
            {"fieldname": "city", "fieldtype": "Data", "label": "City (External)"},
            {"fieldname": "faiss_id", "fieldtype": "Int", "label": "FAISS ID", "description": "ID corresponding to FAISS index", "in_list_view": 1}
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
        ],
        "autoname": "hash"
    })
    doc.insert(ignore_permissions=True)
    print("DocType Candidate created successfully.")
