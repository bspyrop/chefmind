"""
debug/search.py
Test a semantic search query against the ChromaDB index.

Usage:
    python debug/search.py "chicken with lemon"
    python debug/search.py "γαρίδες σάλτσα" --k 4
    python debug/search.py "garlic" --video mw2sEc2_HHs
"""

import os, sys, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def _fmt(sec) -> str:
    m, s = divmod(int(sec or 0), 60)
    return f"{m:02d}:{s:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test a RAG search query")
    parser.add_argument("query",            help="Search query text")
    parser.add_argument("--k",    type=int, default=6,  help="Number of results (default 6)")
    parser.add_argument("--video", default=None,         help="Filter by video_id")
    args = parser.parse_args()

    from rag.retriever import VectorStoreManager

    store   = VectorStoreManager()
    results = store.search(query=args.query, k=args.k, filter_video_id=args.video)

    print(f"\n{'━'*70}")
    print(f"  Query  : {args.query}")
    print(f"  Filter : {args.video or '(none)'}")
    print(f"  k      : {args.k}")
    print(f"  Hits   : {len(results)}")
    print(f"{'━'*70}\n")

    if not results:
        print("  No results found.\n")
        return

    for i, chunk in enumerate(results, 1):
        start = chunk.get("start_time_sec", 0)
        end   = chunk.get("end_time_sec",   0)
        print(f"  [{i}] {chunk.get('title', '?')}  [{_fmt(start)} → {_fmt(end)}]")
        print(f"       video_id : {chunk.get('video_id')}")
        print(f"       url      : {chunk.get('url')}")
        print(f"       text     : {chunk.get('chunk_text', '')}")
        print()

    print(f"{'━'*70}\n")


if __name__ == "__main__":
    main()
