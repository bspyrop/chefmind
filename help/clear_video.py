"""
help/clear_video.py
Remove a single video (all its chunks) from the ChromaDB index and catalog.

Usage:
    python help/clear_video.py <video_id>
    python help/clear_video.py mw2sEc2_HHs
    python help/clear_video.py mw2sEc2_HHs --yes   ← skip confirmation
    python help/clear_video.py                      ← lists indexed videos
"""

import os, sys, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove one video from the index")
    parser.add_argument("video_id", nargs="?", default=None, help="video_id to remove")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    from rag.retriever import VectorStoreManager

    store = VectorStoreManager()

    if not args.video_id:
        catalog = store.get_catalog()
        if not catalog:
            print("\nNo videos indexed yet.\n")
        else:
            print("\nIndexed videos:")
            for v in catalog:
                print(f"  {v['video_id']}  —  {v['title']}")
            print()
        sys.exit(0)

    video_id = args.video_id

    # Check it exists
    result = store._chroma.get(where={"video_id": video_id}, include=[])
    chunk_ids = result.get("ids", [])

    if not chunk_ids:
        print(f"\nNo chunks found for video_id: {video_id!r}\n")
        sys.exit(1)

    title = store._catalog.get(video_id, {}).get("title", "Unknown")

    print(f"\n  Video  : {title}")
    print(f"  ID     : {video_id}")
    print(f"  Chunks : {len(chunk_ids)}\n")

    if not args.yes:
        answer = input("Type 'yes' to confirm deletion: ").strip().lower()
        if answer != "yes":
            print("Aborted.\n")
            sys.exit(0)

    # Delete all chunks for this video from ChromaDB
    store._chroma.delete(ids=chunk_ids)

    # Remove from catalog
    store._catalog.pop(video_id, None)
    store._save_catalog()

    print(f"\n  Removed {len(chunk_ids)} chunks for '{title}'.\n")


if __name__ == "__main__":
    main()
