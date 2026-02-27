"""
help/clear_all.py
Wipe the entire ChromaDB index and catalog — full reset.

Usage:
    python help/clear_all.py
    python help/clear_all.py --yes    ← skip confirmation prompt
"""

import os, sys, shutil, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CHROMA_DIR       = "data/chroma_db"
CATALOG_FILE     = "data/catalog.json"
NUTRITION_DIR    = "data/chroma_nutrition"


def main() -> None:
    parser = argparse.ArgumentParser(description="Wipe the full ChromaDB index and catalog")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    print("\n⚠️  This will delete ALL indexed videos, transcript chunks, and nutrition data.\n")

    if not args.yes:
        answer = input("Type 'yes' to confirm: ").strip().lower()
        if answer != "yes":
            print("Aborted.\n")
            sys.exit(0)

    removed = []

    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        removed.append(CHROMA_DIR)

    if os.path.exists(CATALOG_FILE):
        os.remove(CATALOG_FILE)
        removed.append(CATALOG_FILE)

    if os.path.exists(NUTRITION_DIR):
        shutil.rmtree(NUTRITION_DIR)
        removed.append(NUTRITION_DIR)

    if removed:
        for path in removed:
            print(f"  deleted  {path}")
        print("\nIndex reset complete. Run seed_index.py to re-index videos.\n")
        print("Nutrition data will re-ingest automatically on next nutrition query.\n")
    else:
        print("Nothing to delete — index was already empty.\n")


if __name__ == "__main__":
    main()
