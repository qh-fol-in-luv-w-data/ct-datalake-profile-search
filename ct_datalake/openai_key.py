import frappe
import os
from openai import OpenAI

AGENT_NAME = "2AS-MASTER-PROFILE"

def get_openai_api_key(agent_name=AGENT_NAME):
    try:
        if frappe.db:
            doc = frappe.get_doc("Agent", agent_name)
            val = doc.get_password("api_key")
            if val: return val
    except Exception: pass
    return os.getenv("OPENAI_API_KEY", "")

def get_openai_client():
    key = get_openai_api_key()
    if not key:
        return None
    return OpenAI(api_key=key)
