"""
tools/tools.py
LangChain tool definitions for ChefMind.

All tools share a singleton VectorStoreManager so the same FAISS index is
used across the application. Tools are decorated with @tool so the
LangChain AgentExecutor can call them automatically.

Tools:
  1. rag_search               — semantic search over indexed transcripts
  2. rag_add_youtube_video    — ingest a YouTube URL into the RAG index
  3. get_video_catalog        — list all indexed videos
  4. nutrition_estimate       — estimate nutrition from an ingredient list
  5. parse_recipe_from_transcript — extract a structured recipe from transcript text
"""

import json
import logging
from pathlib import Path
from typing import Optional

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from rag.ingestion import ingest_video
from rag.retriever import NutritionStoreManager, VectorStoreManager

logger = logging.getLogger(__name__)

# ── Shared vector store singletons ────────────────────────────────────────────

_store: Optional[VectorStoreManager] = None
_nutrition_store: Optional[NutritionStoreManager] = None


def get_store() -> VectorStoreManager:
    """Return (or create) the shared VectorStoreManager instance."""
    global _store
    if _store is None:
        _store = VectorStoreManager()
    return _store


def get_nutrition_store() -> NutritionStoreManager:
    """Return (or create) the shared NutritionStoreManager instance.

    Auto-ingests USDA FoodData Central JSON on first access if the
    collection is empty.
    """
    global _nutrition_store
    if _nutrition_store is None:
        _nutrition_store = NutritionStoreManager()
        if _nutrition_store.is_empty():
            _auto_ingest_nutrition(_nutrition_store)
    return _nutrition_store


def _auto_ingest_nutrition(store: NutritionStoreManager) -> None:
    json_path = "data/FoodData_Central_foundation_food_json_2025-12-18.json"
    if not Path(json_path).exists():
        logger.warning("FoodData Central JSON not found at %s — skipping auto-ingest", json_path)
        return
    from rag.nutrition_ingestion import load_nutrition_docs
    logger.info("Auto-ingesting USDA FoodData Central data…")
    docs = load_nutrition_docs(json_path)
    store.add_documents(docs)
    logger.info("Nutrition store ready with %d food items", len(docs))


# ── Tool 1: rag_search ────────────────────────────────────────────────────────

@tool
def rag_search(query: str, k: int = 6, video_id: str = "") -> str:
    """
    Search the indexed YouTube transcripts using semantic similarity.

    Use this tool whenever the user asks about:
    - Recipes, ingredients, or cooking steps
    - Video content or what was said in a video
    - Timestamps for specific actions
    - Any knowledge that should be grounded in indexed videos
    - When say "Show me" or "Present" or "In witch part of the video" or "When" or similar provide timestamps

    Args:
        query:    Natural language search query
        k:        Number of chunks to return (default 6)
        video_id: Optional — restrict results to a specific video ID

    Returns:
        JSON list of matching transcript chunks with metadata.
    """
    store = get_store()
    filter_vid = video_id.strip() if video_id else None
    results = store.search(query=query, k=k, filter_video_id=filter_vid)

    if not results:
        return json.dumps({"results": [], "message": "No matching transcript chunks found."})

    return json.dumps({"results": results})


# ── Tool 2: rag_add_youtube_video ─────────────────────────────────────────────

@tool
def rag_add_youtube_video(url: str) -> str:
    """
    Ingest a YouTube video into the RAG knowledge base.

    This fetches the video's transcript and metadata, chunks the transcript
    into timestamped segments, embeds them, and stores them in the vector DB.

    Use this tool when the user asks to add or index a YouTube video.

    Args:
        url: Full YouTube URL (e.g. https://www.youtube.com/watch?v=...)

    Returns:
        JSON with video_id, title, url, chunks_added, status.
    """
    store = get_store()
    result = ingest_video(url=url, vector_store=store)
    return json.dumps(result)


# ── Tool 3: get_video_catalog ─────────────────────────────────────────────────

@tool
def get_video_catalog() -> str:
    """
    Return a list of all YouTube videos currently indexed in the RAG knowledge base.

    Use this tool when the user asks what videos are available, what has been indexed,
    or wants to browse the catalog.

    Returns:
        JSON list of {video_id, title, url, channel} for each indexed video.
    """
    store = get_store()
    catalog = store.get_catalog()

    if not catalog:
        return json.dumps({"catalog": [], "message": "No videos indexed yet."})

    return json.dumps({"catalog": catalog})


# ── Tool 4: nutrition_estimate ────────────────────────────────────────────────

@tool
def nutrition_estimate(ingredients: list[str], servings: int = 2) -> str:
    """
    Estimate nutritional information for a recipe given its ingredient list.

    Uses an LLM to produce a reasonable per-serving estimate. The result is
    clearly labelled as an estimate, not a certified nutritional analysis.

    Use this tool when the user asks for calories, macros, or nutrition info
    for a recipe.

    Args:
        ingredients: List of ingredient strings (e.g. ["200g chicken breast", "1 tbsp olive oil"])
        servings:    Number of servings (default 2)

    Returns:
        JSON with per_serving estimates for calories, protein_g, carbs_g, fat_g,
        and optional fiber_g / sodium_mg.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    ingredient_list = "\n".join(f"- {item}" for item in ingredients)
    prompt = f"""You are a nutrition expert. Estimate the nutritional content for this recipe.

Ingredients:
{ingredient_list}

Servings: {servings}

Respond ONLY with a JSON object in this exact format (no extra text):
{{
  "per_serving": {{
    "calories": <integer>,
    "protein_g": <number>,
    "carbs_g": <number>,
    "fat_g": <number>,
    "fiber_g": <number>,
    "sodium_mg": <integer>
  }},
  "note": "Estimated values. Not a certified nutritional analysis."
}}"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    # Strip markdown code fences if the model added them
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else content

    try:
        return content  # Already valid JSON from the model
    except Exception:
        return json.dumps({"error": "Could not parse nutrition estimate.", "raw": content})


# ── Tool 5: parse_recipe_from_transcript ─────────────────────────────────────

@tool
def parse_recipe_from_transcript(transcript_text: str) -> str:
    """
    Convert raw transcript text into a structured, user-friendly recipe.

    Use this tool when the user asks to rewrite or format a recipe from a
    video transcript. The returned recipe includes title, ingredients, and
    numbered steps.

    Args:
        transcript_text: Raw transcript text from a YouTube video

    Returns:
        JSON with title, servings, ingredients list, steps list, and optional tips.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    prompt = f"""You are a culinary writer. Extract a clean, structured recipe from this transcript.

Transcript:
{transcript_text[:4000]}

Rules:
- If quantities are not mentioned, write "not specified in transcript"
- Keep steps numbered and clear
- Include up to 3 practical tips if you spot them

Respond ONLY with a JSON object in this exact format (no extra text):
{{
  "title": "...",
  "servings": null,
  "ingredients": ["..."],
  "steps": ["..."],
  "tips": ["..."]
}}"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else content

    return content


# ── Tool 6: nutrition_rag_search ─────────────────────────────────────────────

@tool
def nutrition_rag_search(query: str, k: int = 5) -> str:
    """
    Search the USDA FoodData Central database for precise nutritional data.

    Use this tool when the user asks about:
    - Calories, macros (protein, carbs, fat) for specific foods or ingredients
    - Micronutrients (vitamins, minerals, fiber, sodium) in specific ingredients
    - Nutritional comparison between foods
    - Serving size information for an ingredient

    Prefer this over nutrition_estimate for USDA-grounded, precise data.
    Fall back to nutrition_estimate only if the ingredient is not found here.

    Args:
        query: Natural language food query (e.g. "chicken breast protein",
               "olive oil fat", "calories in brown rice")
        k:     Number of food items to return (default 5)

    Returns:
        JSON list of matching food items with nutrient details per 100g.
    """
    store = get_nutrition_store()
    results = store.search(query=query, k=k)

    if not results:
        return json.dumps(
            {"results": [], "message": "No matching foods found in USDA database."}
        )

    return json.dumps({"results": results})


# ── Exported list of all tools ────────────────────────────────────────────────

ALL_TOOLS = [
    rag_search,
    rag_add_youtube_video,
    get_video_catalog,
    nutrition_rag_search,
    nutrition_estimate,
    parse_recipe_from_transcript,
]
