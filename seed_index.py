"""
seed_index.py
Pre-seed the ChefMind ChromaDB index with a list of YouTube videos.

Usage:
    python seed_index.py

Edit the VIDEOS list below to add your URLs.
A 10-second delay is applied between each video to avoid rate-limiting.

Each transcript chunk is printed to the console before it is stored,
showing its index, timestamps, and the first 120 characters of text.
"""

import time
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Add your YouTube URLs here ────────────────────────────────────────────────

VIDEOS = [
    "https://youtu.be/hkEelgx_J7g?si=Fp0qSfhZhCgIfxKK",
    # add more …
]

DELAY_SECONDS = 10


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_time(seconds: int) -> str:
    """Convert integer seconds to MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _ingest_verbose(url: str, store) -> dict:
    """
    Run the ingestion pipeline step-by-step, printing every chunk to the
    console before it is added to the vector store.
    """
    from rag.ingestion import (
        extract_video_id,
        fetch_metadata,
        fetch_transcript,
        chunk_transcript,
    )

    # Step 1 — extract video ID
    video_id = extract_video_id(url)
    logger.info("  video_id   : %s", video_id)

    # Step 2 — fetch metadata
    metadata = fetch_metadata(video_id)
    logger.info("  title      : %s", metadata["title"])
    logger.info("  channel    : %s", metadata["channel"])
    logger.info("  published  : %s", metadata["published_at"])

    # Step 3 — fetch transcript
    entries = fetch_transcript(video_id)
    logger.info("  transcript : %d raw entries", len(entries))

    # Step 4 — chunk
    docs = chunk_transcript(entries, video_id, metadata)
    logger.info("  chunks     : %d total", len(docs))
    print()

    # Step 5 — log + store each chunk
    for idx, doc in enumerate(docs, 1):
        start = doc.metadata.get("start_time_sec", 0)
        end   = doc.metadata.get("end_time_sec", 0)
        preview = doc.page_content[:120].replace("\n", " ")
        print(
            f"  chunk {idx:>3}/{len(docs)}"
            f"  [{_fmt_time(start)} → {_fmt_time(end)}]"
            f"  {preview}…"
        )
        store.add_documents([doc])   # store one at a time so logs stay in sync

    print()
    return {
        "video_id": video_id,
        "title": metadata["title"],
        "url": metadata["url"],
        "chunks_added": len(docs),
        "status": "ok",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from rag.retriever import VectorStoreManager

    store = VectorStoreManager()
    total = len(VIDEOS)

    logger.info("Starting ingestion of %d video(s).", total)

    for i, url in enumerate(VIDEOS, 1):
        if i > 1:
            logger.info("Waiting %ds before next video…", DELAY_SECONDS)
            time.sleep(DELAY_SECONDS)

        print()
        logger.info("━" * 60)
        logger.info("[%d/%d] %s", i, total, url)
        logger.info("━" * 60)

        try:
            result = _ingest_verbose(url, store)
            logger.info(
                '  ✓ Done — "%s" (%d chunks added)',
                result["title"],
                result["chunks_added"],
            )
        except Exception as exc:
            logger.error("  ✗ FAILED — %s", exc)

    print()
    logger.info("Finished. Index now contains %d video(s).", len(store.get_catalog()))


if __name__ == "__main__":
    main()
