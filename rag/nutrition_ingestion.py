"""
rag/nutrition_ingestion.py
Load and convert USDA FoodData Central JSON into LangChain Documents.

Each foundation food item becomes one Document:
  page_content — human-readable text with food name + key nutrients per 100g
  metadata     — fdc_id, description, category, source

The Documents are stored in a separate ChromaDB collection (chefmind_nutrition)
so they don't mix with YouTube transcript chunks.
"""

import json
import logging
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Nutrient name substrings to include (case-insensitive match)
_KEY_NUTRIENT_KEYWORDS = [
    "energy",
    "protein",
    "total lipid",
    "carbohydrate",
    "fiber",
    "sugars",
    "sodium",
    "calcium",
    "iron",
    "vitamin c",
    "potassium",
    "cholesterol",
    "fatty acids, total saturated",
    "vitamin a",
    "vitamin d",
    "vitamin b-12",
    "folate",
    "zinc",
    "magnesium",
    "phosphorus",
]

_DEFAULT_JSON_PATH = "data/FoodData_Central_foundation_food_json_2025-12-18.json"


def load_nutrition_docs(json_path: str = _DEFAULT_JSON_PATH) -> list[Document]:
    """
    Read FoodData Central foundation food JSON and return one LangChain
    Document per food item, ready for embedding.

    page_content example:
        Hummus, commercial
        Category: Legumes and Legume Products
        Nutrients per 100g:
          - Energy: 229 kcal
          - Protein: 7.35 g
          - Total lipid (fat): 17.1 g
          - Carbohydrate, by difference: 14.9 g
          ...
        Serving sizes: 2 tablespoon = 33.9g
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"FoodData Central JSON not found: {json_path}")

    with open(path) as f:
        data = json.load(f)

    foods = data.get("FoundationFoods", [])
    logger.info("Loaded %d foundation foods from %s", len(foods), json_path)

    docs: list[Document] = []

    for food in foods:
        description = food.get("description", "Unknown Food")
        fdc_id = str(food.get("fdcId", ""))

        # Category
        cat = food.get("foodCategory")
        category = cat.get("description", "") if isinstance(cat, dict) else ""

        # Select and format key nutrients
        nutrient_lines: list[str] = []
        for n in food.get("foodNutrients", []):
            name = n.get("nutrient", {}).get("name", "")
            unit = n.get("nutrient", {}).get("unitName", "")
            amount = n.get("amount")

            if amount is None:
                continue

            name_lower = name.lower()

            # Skip energy in kJ — keep only kcal to avoid duplicate
            if "energy" in name_lower and unit.lower() != "kcal":
                continue

            if any(kw in name_lower for kw in _KEY_NUTRIENT_KEYWORDS):
                nutrient_lines.append(f"  - {name}: {amount} {unit}")

        nutrients_text = (
            "\n".join(nutrient_lines) if nutrient_lines else "  - (no key nutrients found)"
        )

        # Serving sizes
        portion_parts: list[str] = []
        for p in food.get("foodPortions", []):
            mu = p.get("measureUnit", {})
            unit_name = mu.get("name", "")
            gw = p.get("gramWeight")
            amt = p.get("amount")
            if amt and unit_name and gw:
                portion_parts.append(f"{amt} {unit_name} = {gw}g")

        content = (
            f"{description}\n"
            f"Category: {category}\n"
            f"Nutrients per 100g:\n{nutrients_text}"
        )
        if portion_parts:
            content += f"\nServing sizes: {'; '.join(portion_parts)}"

        docs.append(
            Document(
                page_content=content,
                metadata={
                    "fdc_id": fdc_id,
                    "description": description,
                    "category": category,
                    "source": "usda_fooddata_central",
                },
            )
        )

    logger.info("Created %d nutrition documents", len(docs))
    return docs
