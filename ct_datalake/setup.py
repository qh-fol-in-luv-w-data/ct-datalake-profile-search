from setuptools import setup, find_packages

setup(
    name="ct_datalake",
    version="1.0.0",
    description="AI Candidate Search System — Frappe App",
    author="CT Group",
    author_email="dev@ctgroup.vn",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
