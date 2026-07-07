from __future__ import annotations

from app.shared.logging import get_logger


class BaseRepository:
    """Shared base for persistence repositories (StateRepository adapter).

    Historically an empty stub — now the common base every concrete state
    repository (SQLite / TigerGraph) extends, carrying a name for logging so the
    active tier and any fallback are observable in logs/app.log.
    """

    repository_name = "base_repository"

    def __init__(self) -> None:
        self.log = get_logger(f"app.state.{self.repository_name}")
