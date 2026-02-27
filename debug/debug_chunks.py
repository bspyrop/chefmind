"""
debug_chunks.py
Print ALL stored chunks for a given video_id from the ChromaDB index.

Uses ChromaDB's get() with a metadata filter — returns every chunk
for the video, not just the top-k semantic search results.

Usage:
    python debug_chunks.py <video_id>
    python debug_chunks.py mw2sEc2_HHs

    # No argument → lists all indexed video IDs
    python debug_chunks.py
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()


def _fmt_time(seconds) -> str:
    m, s = divmod(int(seconds or 0), 60)
    return f"{m:02d}:{s:02d}"


def main(video_id: str) -> None:
    from rag.retriever import VectorStoreManager

    store = VectorStoreManager()

    # Use ChromaDB's get() to fetch ALL chunks for this video_id
    # (no semantic ranking — pure metadata filter)
    result = store._chroma.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )

    docs      = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not docs:
        print(f"\nNo chunks found for video_id: {video_id!r}\n")
        print("Indexed videos:")
        for v in store.get_catalog():
            print(f"  {v['video_id']}  —  {v['title']}")
        return

    title     = metadatas[0].get("title",        "Unknown") if metadatas else "Unknown"
    channel   = metadatas[0].get("channel",      "Unknown") if metadatas else "Unknown"
    published = metadatas[0].get("published_at", "Unknown") if metadatas else "Unknown"
    url       = metadatas[0].get("url",          "")        if metadatas else ""

    # Sort by start_time_sec so chunks appear in video order
    pairs = sorted(
        zip(docs, metadatas),
        key=lambda x: x[1].get("start_time_sec", 0),
    )

    print(f"\n{'━' * 70}")
    print(f"  video_id   : {video_id}")
    print(f"  title      : {title}")
    print(f"  channel    : {channel}")
    print(f"  published  : {published}")
    print(f"  url        : {url}")
    print(f"  chunks     : {len(pairs)} total")
    print(f"{'━' * 70}\n")

    for i, (text, meta) in enumerate(pairs, 1):
        start   = meta.get("start_time_sec", 0)
        end     = meta.get("end_time_sec",   0)
        cleaned = text.replace("\n", " ")
        print(
            f"  chunk {i:>3}/{len(pairs)}"
            f"  [{_fmt_time(start)} → {_fmt_time(end)}]"
            f"  {cleaned}"
        )

    print(f"\n{'━' * 70}")
    print(f"  Total chunks: {len(pairs)}")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python debug_chunks.py <video_id>\n")
        print("Indexed videos:")
        from rag.retriever import VectorStoreManager
        for v in VectorStoreManager().get_catalog():
            print(f"  {v['video_id']}  —  {v['title']}")
        print()
        sys.exit(0)

    main(sys.argv[1])
