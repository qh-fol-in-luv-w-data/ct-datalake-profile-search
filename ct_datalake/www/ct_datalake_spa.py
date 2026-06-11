import frappe
import os

no_cache = 1

def get_context(context):
    context.no_header = 1
    context.no_sidebar = 1
    context.no_breadcrumbs = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    app_path = frappe.get_app_path("ct_datalake", "public", "frontend", "index.html")
    if os.path.exists(app_path):
        with open(app_path, "r", encoding="utf-8") as f:
            context.vue_html = f.read()
    else:
        context.vue_html = "<div>Please run npm run build in frontend directory of 2as-master-profile.</div>"
    return context
