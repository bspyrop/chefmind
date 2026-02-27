"""
debug/catalog.py
Print the full video catalog and total chunk count per video.

Usage:
    python debug/catalog.py
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def main() -> None:
    from rag.retriever import VectorStoreManager

    store   = VectorStoreManager()
    catalog = store.get_catalog()
    total   = store._chroma._collection.count()

    if not catalog:
        print("\nNo videos indexed yet.\n")
        return

    print(f"\n{'━'*70}")
    print(f"  Indexed videos : {len(catalog)}")
    print(f"  Total chunks   : {total}")
    print(f"{'━'*70}\n")

    for v in catalog:
        result = store._chroma.get(
            where={"video_id": v["video_id"]},
            include=[],  # ids only — fast
        )
        chunk_count = len(result.get("ids", []))

        print(f"  {v['video_id']}  ({chunk_count} chunks)")
        print(f"    Title   : {v['title']}")
        print(f"    Channel : {v.get('channel', '—')}")
        print(f"    URL     : {v['url']}")
        print()

    print(f"{'━'*70}\n")


if __name__ == "__main__":
    main()
