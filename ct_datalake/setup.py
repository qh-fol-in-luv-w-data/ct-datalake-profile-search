from setuptools import setup, find_packages

setup(
    name="ct_datalake",
    version="1.0.0",
    description="AI Candidate Search System",
    author="QH FOL",
    author_email="qh@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
