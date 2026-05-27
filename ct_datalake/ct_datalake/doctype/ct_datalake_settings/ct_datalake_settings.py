# Copyright (c) 2026, QH FOL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CTDataLakeSettings(Document):
    pass


def get_settings() -> "CTDataLakeSettings":
    """Shortcut để lấy settings từ bất kỳ đâu trong app.

    Usage:
        from ct_datalake.ct_datalake.doctype.ct_datalake_settings.ct_datalake_settings import get_settings
        s = get_settings()
        api_key = s.get_password("openai_api_key")
    """
    return frappe.get_single("CT DataLake Settings")
