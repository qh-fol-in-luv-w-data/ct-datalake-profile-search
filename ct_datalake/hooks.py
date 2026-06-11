app_name = "ct_datalake"
app_title = "CT DataLake"
app_publisher = "CT Group"
app_description = "AI Candidate Search System — Frappe App"
app_email = "dev@ctgroup.vn"
app_license = "MIT"

# Expose API
override_whitelisted_methods = {}


# SPA Routing
website_route_rules = [
    {"from_route": "/aicenter/2as-master-profile/<path:app_path>", "to_route": "ct_datalake_spa"},
    {"from_route": "/aicenter/2as-master-profile", "to_route": "ct_datalake_spa"}
]
