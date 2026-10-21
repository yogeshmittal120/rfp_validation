"""Retrieve training courses relevant to incorrectly answered RFP requirements."""
import os
from pathlib import Path
from typing import Any

import chromadb

from .embedding_service import get_embedding_function

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "training_catalogue"


def _get_collection():
    chroma_path = Path(os.getenv("CHROMA_PERSIST_DIRECTORY", str(DEFAULT_CHROMA_PATH)))
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def recommend_training(
    failed_requirements: list[str],
    top_k: int = 5,
    min_similarity: float | None = None,
) -> list[dict[str, Any]]:
    """Search per failed requirement, de-duplicate courses and rank by best similarity."""
    if not failed_requirements:
        return []

    if min_similarity is None:
        min_similarity = float(os.getenv("TRAINING_MIN_SIMILARITY", "0.20"))

    collection = _get_collection()
    if collection.count() == 0:
        return []

    best_by_id: dict[str, dict[str, Any]] = {}
    per_requirement = max(3, min(top_k, 5))

    for requirement in failed_requirements:
        result = collection.query(
            query_texts=[requirement],
            n_results=min(per_requirement, collection.count()),
            include=["metadatas", "distances", "documents"],
        )
        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for training_id, metadata, distance in zip(ids, metadatas, distances):
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            if similarity < min_similarity:
                continue

            existing = best_by_id.get(training_id)
            if existing and existing["relevance_score"] >= similarity:
                continue

            metadata = metadata or {}
            best_by_id[training_id] = {
                "series_name": metadata.get("series_name", ""),
                "description": metadata.get("description", ""),
                "series_url": metadata.get("series_url", ""),
                "stage": metadata.get("stage") or None,
                "architecture": metadata.get("architecture") or None,
                "program_track": metadata.get("program_track") or None,
                "track": metadata.get("track") or None,
                "role": metadata.get("role") or None,
                "language": metadata.get("language") or None,
                "learning_plan_type": metadata.get("learning_plan_type") or None,
                "business_entity": metadata.get("business_entity") or None,
                "matched_requirement": requirement,
                "relevance_score": round(similarity, 4),
            }

    return sorted(
        best_by_id.values(),
        key=lambda item: item["relevance_score"],
        reverse=True,
    )[:top_k]
