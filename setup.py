from setuptools import setup, find_packages

# Chỉ khai báo thư viện nhẹ — thư viện ML nặng được cài qua requirements.txt riêng
INSTALL_REQUIRES = [
    "openai>=1.0.0",
    "pypdf>=3.0.0",
    "python-docx>=0.8.11",
    "python-dotenv>=1.0.0",
    "deep-translator>=1.9.0",
    "requests>=2.28.0",
]

setup(
    name="ct_datalake",
    version="1.0.0",
    description="AI Candidate Search System — Frappe App",
    author="CT Group",
    author_email="dev@ctgroup.vn",
    packages=find_packages(where="ct_datalake"),
    package_dir={"": "ct_datalake"},
    zip_safe=False,
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=INSTALL_REQUIRES,
)

