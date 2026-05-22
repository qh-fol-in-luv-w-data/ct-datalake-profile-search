from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#") and line.strip() != "frappe"
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
    install_requires=install_requires,
)
