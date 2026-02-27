"""
debug/chunks.py
Print ALL stored chunks for a given video_id (sorted by timestamp).

Usage:
    python debug/chunks.py <video_id>
    python debug/chunks.py          ← lists all indexed video IDs
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def _fmt(sec) -> str:
    m, s = divmod(int(sec or 0), 60)
    return f"{m:02d}:{s:02d}"


def main(video_id: str) -> None:
    from rag.retriever import VectorStoreManager

    store = VectorStoreManager()
    result = store._chroma.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )

    docs      = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not docs:
        print(f"\nNo chunks found for video_id: {video_id!r}\n")
        _list_catalog(store)
        return

    title = metadatas[0].get("title", "Unknown")
    url   = metadatas[0].get("url", "")
    pairs = sorted(zip(docs, metadatas), key=lambda x: x[1].get("start_time_sec", 0))

    print(f"\n{'━'*70}")
    print(f"  Video  : {title}")
    print(f"  ID     : {video_id}")
    print(f"  URL    : {url}")
    print(f"  Chunks : {len(pairs)}")
    print(f"{'━'*70}\n")

    for i, (text, meta) in enumerate(pairs, 1):
        print(f"  chunk {i:>3}/{len(pairs)}  [{_fmt(meta.get('start_time_sec'))} → {_fmt(meta.get('end_time_sec'))}]")
        print(f"  {text}\n")

    print(f"{'━'*70}  total: {len(pairs)} chunks\n")


def _list_catalog(store=None) -> None:
    from rag.retriever import VectorStoreManager
    if store is None:
        store = VectorStoreManager()
    catalog = store.get_catalog()
    if not catalog:
        print("No videos indexed yet.")
        return
    print("Indexed videos:")
    for v in catalog:
        print(f"  {v['video_id']}  —  {v['title']}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python debug/chunks.py <video_id>\n")
        _list_catalog()
        sys.exit(0)
    main(sys.argv[1])
