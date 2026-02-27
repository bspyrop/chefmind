"""
rag/ingestion.py
YouTube ingestion pipeline for ChefMind.

Pipeline:
  1. Extract video_id from URL
  2. Fetch metadata via yt-dlp (title, channel, published_at)
  3. Fetch transcript with timestamps via youtube-transcript-api
  4. Chunk transcript into ~60-second / ~400-token windows
  5. Wrap each chunk as a LangChain Document with full metadata
  6. Embed + upsert via the VectorStoreManager
"""

import re
import json
import logging
from typing import TYPE_CHECKING

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document

if TYPE_CHECKING:
    from rag.retriever import VectorStoreManager

logger = logging.getLogger(__name__)

# ── Tuneable chunking parameters ──────────────────────────────────────────────
CHUNK_MAX_SECONDS = 10   # combine transcript entries until this window closes
CHUNK_MAX_TOKENS = 400   # rough token ceiling (1 token ≈ 4 characters)


# ── 1. Extract video ID ───────────────────────────────────────────────────────

def extract_video_id(url: str) -> str:
    """Parse a YouTube URL and return the 11-character video ID."""
    patterns = [
        r"(?:v=|youtu\.be/|/embed/|/v/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract a YouTube video ID from: {url!r}")


# ── 2. Fetch video metadata ───────────────────────────────────────────────────

def fetch_metadata(video_id: str) -> dict:
    """
    Use yt-dlp to fetch video metadata without downloading the video.
    Returns a dict with title, channel, published_at, url.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    published_at = info.get("upload_date", "")
    # Convert YYYYMMDD → YYYY-MM-DD
    if len(published_at) == 8:
        published_at = f"{published_at[:4]}-{published_at[4:6]}-{published_at[6:]}"

    return {
        "video_id": video_id,
        "title": info.get("title", "Unknown Title"),
        "channel": info.get("uploader", "Unknown Channel"),
        "published_at": published_at,
        "url": url,
    }


# ── 3. Fetch transcript ───────────────────────────────────────────────────────

def fetch_transcript(video_id: str) -> list[dict]:
    """
    Fetch the transcript for a video using youtube-transcript-api (v1+).
    Returns a list of entries: [{text, start, duration}, ...].
    Falls back to auto-generated captions if no manual transcript exists.
    """
    ytt = YouTubeTranscriptApi()
    transcript_list = ytt.list(video_id)

    # Prefer manual English, then auto-generated
    try:
        transcript = transcript_list.find_manually_created_transcript(["en"])
    except Exception:
        try:
            transcript = transcript_list.find_generated_transcript(["en"])
        except Exception:
            # Last resort: take the first available transcript
            transcript = next(iter(transcript_list))

    return transcript.fetch().to_raw_data()


# ── 4. Chunk transcript ───────────────────────────────────────────────────────

def chunk_transcript(
    entries: list[dict],
    video_id: str,
    metadata: dict,
) -> list[Document]:
    """
    Combine consecutive transcript entries into chunks.
    A new chunk starts when the window exceeds CHUNK_MAX_SECONDS or
    CHUNK_MAX_TOKENS (rough estimate via character count / 4).

    Each returned Document has:
      page_content  — the chunk text
      metadata      — video_id, title, channel, url, published_at,
                      start_time_sec, end_time_sec
    """
    docs: list[Document] = []
    if not entries:
        return docs

    current_texts: list[str] = []
    current_start: float = entries[0]["start"]
    current_end: float = entries[0]["start"]

    def _flush(texts, start, end):
        text = " ".join(texts).strip()
        if not text:
            return
        docs.append(Document(
            page_content=text,
            metadata={
                **metadata,
                "start_time_sec": int(start),
                "end_time_sec": int(end),
            },
        ))

    for entry in entries:
        entry_start: float = entry["start"]
        entry_end: float = entry_start + entry.get("duration", 0)
        entry_text: str = entry["text"].strip()

        window_seconds = entry_end - current_start
        approx_tokens = sum(len(t) for t in current_texts) // 4

        if current_texts and (
            window_seconds > CHUNK_MAX_SECONDS or approx_tokens > CHUNK_MAX_TOKENS
        ):
            _flush(current_texts, current_start, current_end)
            current_texts = [entry_text]
            current_start = entry_start
        else:
            current_texts.append(entry_text)

        current_end = entry_end

    # Flush the last chunk
    _flush(current_texts, current_start, current_end)
    return docs


# ── 5. Full ingestion pipeline ────────────────────────────────────────────────

def ingest_video(url: str, vector_store: "VectorStoreManager") -> dict:
    """
    End-to-end ingestion pipeline:
      1. Extract video_id
      2. Fetch metadata
      3. Fetch transcript
      4. Chunk
      5. Upsert to vector store

    Returns: {video_id, title, url, chunks_added, status}
    """
    try:
        video_id = extract_video_id(url)
        logger.info("Ingesting video %s …", video_id)

        metadata = fetch_metadata(video_id)
        logger.info("Metadata fetched: %s", metadata["title"])

        entries = fetch_transcript(video_id)
        logger.info("Transcript fetched: %d entries", len(entries))

        docs = chunk_transcript(entries, video_id, metadata)
        logger.info("Chunked into %d documents", len(docs))

        vector_store.add_documents(docs)

        return {
            "video_id": video_id,
            "title": metadata["title"],
            "url": metadata["url"],
            "chunks_added": len(docs),
            "status": "ok",
        }

    except Exception as exc:
        logger.exception("Ingestion failed for %s", url)
        return {
            "video_id": None,
            "title": None,
            "url": url,
            "chunks_added": 0,
            "status": f"error: {exc}",
        }
