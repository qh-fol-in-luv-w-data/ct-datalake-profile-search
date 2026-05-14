import frappe
import sys
from ct_datalake.ct_datalake.search import search

def run():
    from ct_datalake.ct_datalake.search import search
    res = search("machine learning", mode="out", top_k=2)
    print("Results length:", len(res))
    if len(res) > 0:
        print("First result:", res[0])

if __name__ == "__main__":
    pass
