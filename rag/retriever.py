"""
rag/retriever.py
ChromaDB vector store wrapper for ChefMind.

Responsibilities:
  - Persist the Chroma collection to disk (data/chroma_db/)
  - Maintain a catalog of indexed videos (data/catalog.json)
  - Provide search with native video_id metadata filtering
  - Expose the video catalog for the UI and tools

ChromaDB advantage over FAISS: native metadata filtering via the `where`
parameter — no need to over-fetch and post-filter results.
"""

import json
import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

_DEFAULT_PERSIST_DIR = "data/chroma_db"
_DEFAULT_CATALOG_PATH = "data/catalog.json"
_COLLECTION_NAME = "chefmind_transcripts"

_NUTRITION_PERSIST_DIR = "data/chroma_nutrition"
_NUTRITION_COLLECTION = "chefmind_nutrition"


class VectorStoreManager:
    """
    Wraps a LangChain Chroma vector store with catalog management and persistence.

    Usage:
        store = VectorStoreManager()
        store.add_documents(docs)
        results = store.search("pasta with tomato", k=6)
        catalog = store.get_catalog()
    """

    def __init__(
        self,
        persist_dir: str = _DEFAULT_PERSIST_DIR,
        catalog_path: str = _DEFAULT_CATALOG_PATH,
    ):
        self.persist_dir = persist_dir
        self.catalog_path = catalog_path
        self.embeddings = OpenAIEmbeddings()
        self._catalog: dict[str, dict] = {}  # video_id → {title, url, channel}

        # Ensure data directory exists
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        # ChromaDB auto-loads existing data from persist_dir on init
        self._chroma = Chroma(
            collection_name=_COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )

        self._load_catalog()
        logger.info(
            "ChromaDB ready (%d chunks, %d videos)",
            self._chroma._collection.count(),
            len(self._catalog),
        )

    # ── Catalog persistence ───────────────────────────────────────────────────

    def _load_catalog(self) -> None:
        """Load the video catalog from disk if it exists."""
        if Path(self.catalog_path).exists():
            try:
                with open(self.catalog_path) as f:
                    self._catalog = json.load(f)
                logger.info("Loaded catalog with %d videos", len(self._catalog))
            except Exception as exc:
                logger.warning("Could not load catalog: %s", exc)
                self._catalog = {}

    def _save_catalog(self) -> None:
        """Persist the video catalog to disk."""
        Path(self.catalog_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.catalog_path, "w") as f:
            json.dump(self._catalog, f, indent=2)

    # ── Add documents ─────────────────────────────────────────────────────────

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed and add documents to the Chroma collection.
        ChromaDB persists automatically — no explicit save call needed.
        Also updates the catalog.
        """
        if not docs:
            logger.warning("add_documents called with empty list")
            return

        self._chroma.add_documents(docs)

        # Update catalog from document metadata
        for doc in docs:
            meta = doc.metadata
            vid = meta.get("video_id")
            if vid and vid not in self._catalog:
                self._catalog[vid] = {
                    "video_id": vid,
                    "title": meta.get("title", "Unknown"),
                    "url": meta.get("url", ""),
                    "channel": meta.get("channel", ""),
                }

        self._save_catalog()
        logger.info(
            "Added %d documents; catalog now has %d videos",
            len(docs),
            len(self._catalog),
        )

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        k: int = 6,
        filter_video_id: str | None = None,
    ) -> list[dict]:
        """
        Semantic similarity search with optional native video_id filter.

        ChromaDB supports the `where` metadata filter natively, so results
        are already scoped to the requested video — no over-fetching needed.
        """
        if self._chroma._collection.count() == 0:
            logger.warning("search called on empty collection")
            return []

        where = {"video_id": filter_video_id} if filter_video_id else None

        results = self._chroma.similarity_search_with_score(query, k=k, filter=where)

        return [
            {
                "video_id": doc.metadata.get("video_id"),
                "title": doc.metadata.get("title"),
                "url": doc.metadata.get("url"),
                "chunk_text": doc.page_content,
                "start_time_sec": doc.metadata.get("start_time_sec"),
                "end_time_sec": doc.metadata.get("end_time_sec"),
                "score": round(float(score), 4),
            }
            for doc, score in results
        ]

    # ── Catalog ───────────────────────────────────────────────────────────────

    def get_catalog(self) -> list[dict]:
        """Return a list of all indexed videos: [{video_id, title, url}, ...]."""
        return list(self._catalog.values())

    def is_empty(self) -> bool:
        """True if no documents have been indexed yet."""
        return self._chroma._collection.count() == 0



class NutritionStoreManager:
    """
    ChromaDB vector store for USDA FoodData Central nutrition data.

    Kept in a separate collection from YouTube transcripts so that
    nutrition searches are scoped to food items only.
    """

    def __init__(self, persist_dir: str = _NUTRITION_PERSIST_DIR):
        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.embeddings = OpenAIEmbeddings()

        self._chroma = Chroma(
            collection_name=_NUTRITION_COLLECTION,
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )
        logger.info(
            "NutritionStore ready (%d docs)", self._chroma._collection.count()
        )

    def add_documents(self, docs: list[Document]) -> None:
        if not docs:
            return
        self._chroma.add_documents(docs)
        logger.info("Added %d nutrition documents", len(docs))

    def search(self, query: str, k: int = 6) -> list[dict]:
        if self._chroma._collection.count() == 0:
            return []
        results = self._chroma.similarity_search_with_score(query, k=k)
        return [
            {
                "fdc_id": doc.metadata.get("fdc_id"),
                "description": doc.metadata.get("description"),
                "category": doc.metadata.get("category"),
                "chunk_text": doc.page_content,
                "score": round(float(score), 4),
                "source": doc.metadata.get("source"),
            }
            for doc, score in results
        ]

    def is_empty(self) -> bool:
        return self._chroma._collection.count() == 0
