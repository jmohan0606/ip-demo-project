"""StateRepository — durable-state persistence adapter (memory, feedback/learning,
impact ledger, recommendation status), following the GraphClient/LLMClient adapter
pattern so TigerGraph can be the source of truth with an automatic SQLite fallback.

Per DATABASES.md, all of this state was hardcoded to SQLite with no seam. This adapter
introduces the seam:

    STATE_STORE_MODE=tigergraph  (default)  → TigerGraphStateRepository PRIMARY, SQLite FALLBACK
    STATE_STORE_MODE=sqlite                 → SqliteStateRepository only (legacy)

Every app-logic state access should go through get_state_repository(). The TigerGraph tier
writes state as graph vertices/edges via the existing GraphClient and reads it back by graph
traversal (installed GQ queries in real mode, their mock equivalents in mock mode). The SQLite
tier retains the exact current logic, and the fallback wrapper degrades to it (logged, never
crashing) if a graph write/read fails — the safety net for the client env's first run.

This module currently covers the MEMORY domain end-to-end; feedback/impact/status domains are
being migrated onto the same seam (see PROGRESS.md for status).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.config.settings import get_settings
from app.models.memory import ContextMemory, ConversationTurn, MemoryScopeType, MemoryType, ReasoningTrace
from app.repositories.base_repository import BaseRepository
from app.shared.logging import get_logger

_log = get_logger("app.state")


@runtime_checkable
class StateRepository(Protocol):
    """The one interface every state access depends on."""

    # --- Memory (6 types share phx_dm_context_memory, discriminated by memory_type) ---
    def save_memory(self, memory: ContextMemory) -> None: ...
    def retrieve_memories(
        self, scope_type: MemoryScopeType, scope_id: str,
        memory_types: list[MemoryType] | None = None, limit: int = 10, include_expired: bool = False,
    ) -> list[ContextMemory]: ...
    def save_conversation_turn(self, turn: ConversationTurn) -> None: ...
    def save_reasoning_trace(self, trace: ReasoningTrace) -> None: ...
    def memory_counts_by_type(self) -> list[dict]: ...

    def describe(self) -> dict: ...


def _memory_from_attrs(attrs: dict) -> ContextMemory:
    """Map a phx_dm_context_memory graph-vertex attribute dict → ContextMemory."""
    def _dt(v, default=None):
        if not v:
            return default
        try:
            return datetime.fromisoformat(str(v))
        except ValueError:
            return default
    facts = attrs.get("facts_json") or attrs.get("facts") or "{}"
    if isinstance(facts, str):
        try:
            facts = json.loads(facts)
        except json.JSONDecodeError:
            facts = {}
    return ContextMemory(
        memory_id=str(attrs.get("memory_id")),
        memory_type=MemoryType(attrs["memory_type"]),
        scope_type=MemoryScopeType(attrs["scope_type"]),
        scope_id=str(attrs.get("scope_id")),
        title=str(attrs.get("title") or ""),
        summary=str(attrs.get("summary") or ""),
        facts=facts if isinstance(facts, dict) else {},
        confidence=float(attrs.get("confidence") or 0.0),
        source=str(attrs.get("source") or "graph"),
        valid_from=_dt(attrs.get("valid_from"), datetime.utcnow()),
        valid_to=_dt(attrs.get("valid_to")),
        created_ts=_dt(attrs.get("created_ts"), datetime.utcnow()),
        status=str(attrs.get("status") or "Active"),
    )


class SqliteStateRepository(BaseRepository):
    """Legacy tier — delegates to the existing SQLite-backed repositories verbatim,
    so behavior is byte-identical to before the adapter. Retained as the fallback."""

    repository_name = "sqlite"

    def __init__(self) -> None:
        super().__init__()
        from app.graph.memory.memory_repository import MemoryRepository

        self._mem = MemoryRepository()

    def save_memory(self, memory: ContextMemory) -> None:
        self._mem.save_memory(memory)

    def retrieve_memories(self, scope_type, scope_id, memory_types=None, limit=10, include_expired=False):
        return self._mem.retrieve_memories(scope_type, scope_id, memory_types, limit, include_expired)

    def save_conversation_turn(self, turn: ConversationTurn) -> None:
        self._mem.save_conversation_turn(turn)

    def save_reasoning_trace(self, trace: ReasoningTrace) -> None:
        self._mem.save_reasoning_trace(trace)

    def memory_counts_by_type(self) -> list[dict]:
        return self._mem.memory_counts_by_type()

    def describe(self) -> dict:
        return {"tier": "sqlite", "authority": "SQLite (legacy)"}


class TigerGraphStateRepository(BaseRepository):
    """PRIMARY tier — writes state as graph vertices/edges via the GraphClient (reusing
    TigerGraphMemoryLinker), reads it back by graph TRAVERSAL (installed GQ queries in
    real mode, mock equivalents in mock mode). This makes TigerGraph the source of truth."""

    repository_name = "tigergraph"

    def __init__(self) -> None:
        super().__init__()
        from app.graph.memory.tigergraph_memory_linker import TigerGraphMemoryLinker

        self._linker = TigerGraphMemoryLinker()

    def _graph(self):
        from app.graph.client import get_graph_client

        return get_graph_client()

    def save_memory(self, memory: ContextMemory) -> None:
        self._linker.upsert_memory(memory)  # upserts vertex + memory_for_<scope> edge

    def retrieve_memories(self, scope_type, scope_id, memory_types=None, limit=10, include_expired=False):
        result = self._graph().run_query("get_context_memory_by_scope", {
            "scope_type": scope_type.value.upper(),
            "scope_id": scope_id,
            "memory_types": [m.value for m in memory_types] if memory_types else [],
            "include_expired": include_expired,
            "result_limit": limit,
        })
        rows = result.get("results", []) if isinstance(result, dict) else (result or [])
        return [_memory_from_attrs(r) for r in rows]

    def save_conversation_turn(self, turn: ConversationTurn) -> None:
        self._linker.upsert_conversation_turn(turn)

    def save_reasoning_trace(self, trace: ReasoningTrace) -> None:
        self._linker.upsert_reasoning_trace(trace)

    def memory_counts_by_type(self) -> list[dict]:
        # Count context-memory vertices grouped by memory_type via the graph store.
        store = self._graph().store
        counts: dict[str, int] = {}
        for attrs in store.all_vertices("phx_dm_context_memory").values():
            mt = str(attrs.get("memory_type") or "Unknown")
            counts[mt] = counts.get(mt, 0) + 1
        return [{"memory_type": k, "memory_count": v}
                for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]

    def describe(self) -> dict:
        return {"tier": "tigergraph", "authority": "TigerGraph (graph vertices/edges)"}


class FallbackStateRepository(BaseRepository):
    """Composes primary + fallback: try the primary tier, and on ANY failure log it
    and degrade to the fallback tier — the graph is authority, SQLite is the safety net."""

    repository_name = "fallback"

    def __init__(self, primary: StateRepository, fallback: StateRepository) -> None:
        super().__init__()
        self.primary = primary
        self.fallback = fallback

    def _both_write(self, op: str, fn):
        """Writes go to the primary (authority); we ALSO mirror to the fallback so the
        SQLite safety net stays warm and a later read-fallback still finds the data."""
        primary_ok = True
        try:
            fn(self.primary)
        except Exception as exc:  # noqa: BLE001
            primary_ok = False
            _log.error("state write %s failed on primary tier; continuing on fallback: %s",
                       op, exc, exc_info=True, extra={"op": op, "tier": "primary"})
        try:
            fn(self.fallback)
        except Exception as exc:  # noqa: BLE001
            if primary_ok:
                _log.warning("state write %s fallback-mirror failed (primary ok): %s", op, exc)
            else:
                _log.error("state write %s failed on BOTH tiers: %s", op, exc, exc_info=True)
                raise

    def _read(self, op: str, fn):
        try:
            return fn(self.primary)
        except Exception as exc:  # noqa: BLE001
            _log.error("state read %s failed on primary tier; falling back to SQLite: %s",
                       op, exc, exc_info=True, extra={"op": op, "tier": "primary"})
            return fn(self.fallback)

    def save_memory(self, memory: ContextMemory) -> None:
        self._both_write("save_memory", lambda r: r.save_memory(memory))

    def retrieve_memories(self, scope_type, scope_id, memory_types=None, limit=10, include_expired=False):
        rows = self._read("retrieve_memories",
                          lambda r: r.retrieve_memories(scope_type, scope_id, memory_types, limit, include_expired))
        # If the graph legitimately has nothing yet (e.g. history not seeded), fall back to
        # SQLite so we never regress below what SQLite already had.
        if not rows and self.primary is not self.fallback:
            rows = self.fallback.retrieve_memories(scope_type, scope_id, memory_types, limit, include_expired)
        return rows

    def save_conversation_turn(self, turn: ConversationTurn) -> None:
        self._both_write("save_conversation_turn", lambda r: r.save_conversation_turn(turn))

    def save_reasoning_trace(self, trace: ReasoningTrace) -> None:
        self._both_write("save_reasoning_trace", lambda r: r.save_reasoning_trace(trace))

    def memory_counts_by_type(self) -> list[dict]:
        return self._read("memory_counts_by_type", lambda r: r.memory_counts_by_type())

    def describe(self) -> dict:
        return {"tier": "fallback", "primary": self.primary.describe(), "fallback": self.fallback.describe()}


_state_repo: StateRepository | None = None


def get_state_repository() -> StateRepository:
    """Select the StateRepository per STATE_STORE_MODE (tigergraph | sqlite)."""
    global _state_repo
    if _state_repo is None:
        mode = getattr(get_settings(), "state_store_mode", "tigergraph").lower()
        if mode == "sqlite":
            _state_repo = SqliteStateRepository()
        else:  # tigergraph (default): graph authority + SQLite fallback
            _state_repo = FallbackStateRepository(TigerGraphStateRepository(), SqliteStateRepository())
        _log.info("StateRepository initialized: %s", _state_repo.describe())
    return _state_repo


def reset_state_repository() -> None:
    global _state_repo
    _state_repo = None
