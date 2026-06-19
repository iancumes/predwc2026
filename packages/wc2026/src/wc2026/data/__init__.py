"""Data ingestion and loading."""
from wc2026.data.ingest import ingest, load_matches
from wc2026.data.tournament import (
    Tournament,
    load_tournament,
)

__all__ = ["ingest", "load_matches", "Tournament", "load_tournament"]
