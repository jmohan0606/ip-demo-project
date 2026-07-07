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

    # --- Learning / bandit weights (RL signal) ---
    def get_learning_weight(self, family: str) -> float: ...
    def apply_learning_delta(self, family: str, delta: float, updated_at: str) -> float: ...
    def all_learning_weights(self) -> list[dict]: ...

    # --- Impact ledger (completion → recorded revenue impact) ---
    def add_impact_entry(self, entry: dict) -> None: ...
    def impact_entries_for_advisor(self, advisor_id: str) -> list[dict]: ...
    def impact_entry_for_recommendation(self, recommendation_id: str) -> dict | None: ...
    def all_impact_entries(self) -> list[dict]: ...

    # --- Recommendation status + status-transition audit trail ---
    def get_rec_status(self, recommendation_id: str) -> str | None: ...
    def set_rec_status(self, recommendation_id: str, status: str, note: str | None = None) -> None: ...
    def record_transition(self, transition: dict) -> None: ...
    def transitions_for(self, recommendation_id: str) -> list[dict]: ...

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

    # --- SQLite tier for weights / impact / status (same tables as before) ---
    def _conn(self):
        import sqlite3
        from pathlib import Path

        path = get_settings().sqlite_db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_weights (
            family TEXT PRIMARY KEY, weight REAL NOT NULL, feedback_count INTEGER NOT NULL, updated_at TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS phx_dm_local_impact_ledger (
            ledger_id TEXT PRIMARY KEY, recommendation_id TEXT, advisor_id TEXT, opportunity_id TEXT,
            action_family TEXT, impact_amount REAL, impact_type TEXT, source_transaction_id TEXT,
            note TEXT, created_ts TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS phx_dm_local_rec_status_transition (
            transition_id TEXT PRIMARY KEY, recommendation_id TEXT, advisor_id TEXT, from_status TEXT,
            to_status TEXT, action TEXT, actor_type TEXT, actor_id TEXT, note TEXT, created_ts TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS phx_dm_local_recommendation (
            recommendation_id TEXT PRIMARY KEY, status TEXT, status_note TEXT, updated_ts TEXT)""")
        return conn

    def get_learning_weight(self, family: str) -> float:
        with self._conn() as c:
            row = c.execute("SELECT weight FROM learning_weights WHERE family=?", (family,)).fetchone()
        return float(row[0]) if row else 1.0

    def apply_learning_delta(self, family: str, delta: float, updated_at: str) -> float:
        new_weight = round(max(0.5, min(1.5, self.get_learning_weight(family) + delta)), 4)
        with self._conn() as c:
            c.execute("INSERT INTO learning_weights (family, weight, feedback_count, updated_at) VALUES (?,?,1,?) "
                      "ON CONFLICT(family) DO UPDATE SET weight=?, feedback_count=feedback_count+1, updated_at=?",
                      (family, new_weight, updated_at, new_weight, updated_at))
            c.commit()
        return new_weight

    def all_learning_weights(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT family, weight, feedback_count, updated_at FROM learning_weights ORDER BY family").fetchall()
        return [{"family": f, "weight": w, "feedback_count": n, "updated_at": u} for f, w, n, u in rows]

    def add_impact_entry(self, entry: dict) -> None:
        with self._conn() as c:
            c.execute("""INSERT OR REPLACE INTO phx_dm_local_impact_ledger
                (ledger_id, recommendation_id, advisor_id, opportunity_id, action_family,
                 impact_amount, impact_type, source_transaction_id, note, created_ts)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (entry["ledger_id"], entry.get("recommendation_id"), entry.get("advisor_id"),
                 entry.get("opportunity_id"), entry.get("action_family"), entry.get("impact_amount"),
                 entry.get("impact_type", "REVENUE"), entry.get("source_transaction_id"),
                 entry.get("note"), entry.get("created_ts")))
            c.commit()

    def _impact_rows(self, where: str = "", params: tuple = ()) -> list[dict]:
        cols = ["ledger_id", "recommendation_id", "advisor_id", "opportunity_id", "action_family",
                "impact_amount", "impact_type", "source_transaction_id", "note", "created_ts"]
        with self._conn() as c:
            rows = c.execute(f"SELECT {','.join(cols)} FROM phx_dm_local_impact_ledger {where}", params).fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def impact_entries_for_advisor(self, advisor_id: str) -> list[dict]:
        return self._impact_rows("WHERE advisor_id=? ORDER BY created_ts DESC", (advisor_id,))

    def impact_entry_for_recommendation(self, recommendation_id: str) -> dict | None:
        rows = self._impact_rows("WHERE recommendation_id=?", (recommendation_id,))
        return rows[0] if rows else None

    def all_impact_entries(self) -> list[dict]:
        return self._impact_rows("ORDER BY created_ts DESC")

    def get_rec_status(self, recommendation_id: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT status FROM phx_dm_local_recommendation WHERE recommendation_id=?",
                            (recommendation_id,)).fetchone()
        return row[0] if row else None

    def set_rec_status(self, recommendation_id: str, status: str, note: str | None = None) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute("""INSERT INTO phx_dm_local_recommendation (recommendation_id, status, status_note, updated_ts)
                VALUES (?,?,?,?) ON CONFLICT(recommendation_id) DO UPDATE SET status=excluded.status,
                status_note=COALESCE(excluded.status_note, phx_dm_local_recommendation.status_note),
                updated_ts=excluded.updated_ts""", (recommendation_id, status, note, now))
            c.commit()

    def record_transition(self, transition: dict) -> None:
        with self._conn() as c:
            c.execute("""INSERT INTO phx_dm_local_rec_status_transition
                (transition_id, recommendation_id, advisor_id, from_status, to_status, action,
                 actor_type, actor_id, note, created_ts) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (transition["transition_id"], transition.get("recommendation_id"), transition.get("advisor_id"),
                 transition.get("from_status"), transition.get("to_status"), transition.get("action"),
                 transition.get("actor_type"), transition.get("actor_id"), transition.get("note"),
                 transition.get("created_ts")))
            c.commit()

    def transitions_for(self, recommendation_id: str) -> list[dict]:
        cols = ["transition_id", "recommendation_id", "advisor_id", "from_status", "to_status",
                "action", "actor_type", "actor_id", "note", "created_ts"]
        with self._conn() as c:
            rows = c.execute(f"SELECT {','.join(cols)} FROM phx_dm_local_rec_status_transition "
                             "WHERE recommendation_id=? ORDER BY created_ts", (recommendation_id,)).fetchall()
        return [dict(zip(cols, r)) for r in rows]

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
        from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient

        self._linker = TigerGraphMemoryLinker()
        self._upsert = TigerGraphUpsertClient()

    def _rows(self, query: str, params: dict) -> list[dict]:
        result = self._graph().run_query(query, params)
        return result.get("results", []) if isinstance(result, dict) else (result or [])

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

    # --- Learning weights: phx_dm_learning_weight vertex per family ---
    def get_learning_weight(self, family: str) -> float:
        rows = self._rows("get_learning_weights", {"family": family})
        return float(rows[0]["weight"]) if rows and rows[0].get("weight") is not None else 1.0

    def apply_learning_delta(self, family: str, delta: float, updated_at: str) -> float:
        current = self.get_learning_weight(family)
        rows = self._rows("get_learning_weights", {"family": family})
        count = int(rows[0].get("feedback_count") or 0) + 1 if rows else 1
        new_weight = round(max(0.5, min(1.5, current + delta)), 4)
        self._upsert.upsert_vertex("phx_dm_learning_weight", family, {
            "family": family, "weight": new_weight, "feedback_count": count, "updated_at": updated_at,
        }, id_column="family")
        return new_weight

    def all_learning_weights(self) -> list[dict]:
        return self._rows("get_learning_weights", {})

    # --- Impact ledger: phx_dm_impact_ledger vertex + edges to advisor/recommendation ---
    def add_impact_entry(self, entry: dict) -> None:
        lid = entry["ledger_id"]
        self._upsert.upsert_vertex("phx_dm_impact_ledger", lid, {
            k: entry.get(k) for k in ("recommendation_id", "advisor_id", "opportunity_id", "action_family",
                                      "impact_amount", "impact_type", "source_transaction_id", "note", "created_ts")
        }, id_column="ledger_id")
        if entry.get("advisor_id"):
            self._upsert.upsert_edge("phx_dm_impact_for_advisor", lid, entry["advisor_id"], {},
                                     from_type="phx_dm_impact_ledger", to_type="phx_dm_advisor")
        if entry.get("recommendation_id"):
            self._upsert.upsert_edge("phx_dm_impact_from_recommendation", lid, entry["recommendation_id"], {},
                                     from_type="phx_dm_impact_ledger", to_type="phx_dm_recommendation")

    def impact_entries_for_advisor(self, advisor_id: str) -> list[dict]:
        return self._rows("get_impact_ledger", {"advisor_id": advisor_id})

    def impact_entry_for_recommendation(self, recommendation_id: str) -> dict | None:
        rows = self._rows("get_impact_ledger", {"recommendation_id": recommendation_id})
        return rows[0] if rows else None

    def all_impact_entries(self) -> list[dict]:
        return self._rows("get_impact_ledger", {})

    # --- Rec status (on the recommendation vertex) + transition audit vertices ---
    def get_rec_status(self, recommendation_id: str) -> str | None:
        # Derive from the latest transition (traversal-based, real-mode safe).
        trns = self.transitions_for(recommendation_id)
        return trns[-1]["to_status"] if trns else None

    def set_rec_status(self, recommendation_id: str, status: str, note: str | None = None) -> None:
        attrs = {"recommendation_id": recommendation_id, "status": status}
        if note is not None:
            attrs["status_note"] = note
        self._upsert.upsert_vertex("phx_dm_recommendation", recommendation_id, attrs,
                                   id_column="recommendation_id")

    def record_transition(self, transition: dict) -> None:
        tid = transition["transition_id"]
        self._upsert.upsert_vertex("phx_dm_rec_status_transition", tid, {
            k: transition.get(k) for k in ("recommendation_id", "advisor_id", "from_status", "to_status",
                                           "action", "actor_type", "actor_id", "note", "created_ts")
        }, id_column="transition_id")
        if transition.get("recommendation_id"):
            self._upsert.upsert_edge("phx_dm_transition_of_recommendation", tid, transition["recommendation_id"], {},
                                     from_type="phx_dm_rec_status_transition", to_type="phx_dm_recommendation")

    def transitions_for(self, recommendation_id: str) -> list[dict]:
        return self._rows("get_rec_status_transitions", {"recommendation_id": recommendation_id})

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

    # --- weights ---
    def get_learning_weight(self, family: str) -> float:
        val = self._read("get_learning_weight", lambda r: r.get_learning_weight(family))
        if val == 1.0 and self.primary is not self.fallback:  # neutral may mean "not in graph yet"
            fb = self.fallback.get_learning_weight(family)
            if fb != 1.0:
                return fb
        return val

    def apply_learning_delta(self, family: str, delta: float, updated_at: str) -> float:
        new_val = 1.0
        primary_ok = True
        try:
            new_val = self.primary.apply_learning_delta(family, delta, updated_at)
        except Exception as exc:  # noqa: BLE001
            primary_ok = False
            _log.error("apply_learning_delta failed on primary; using fallback: %s", exc, exc_info=True)
            new_val = self.fallback.apply_learning_delta(family, delta, updated_at)
        if primary_ok:  # keep SQLite mirror warm
            try:
                self.fallback.apply_learning_delta(family, delta, updated_at)
            except Exception as exc:  # noqa: BLE001
                _log.warning("apply_learning_delta fallback-mirror failed (primary ok): %s", exc)
        return new_val

    def all_learning_weights(self) -> list[dict]:
        rows = self._read("all_learning_weights", lambda r: r.all_learning_weights())
        if not rows and self.primary is not self.fallback:
            rows = self.fallback.all_learning_weights()
        return rows

    # --- impact ledger ---
    def add_impact_entry(self, entry: dict) -> None:
        self._both_write("add_impact_entry", lambda r: r.add_impact_entry(entry))

    def impact_entries_for_advisor(self, advisor_id: str) -> list[dict]:
        rows = self._read("impact_entries_for_advisor", lambda r: r.impact_entries_for_advisor(advisor_id))
        if not rows and self.primary is not self.fallback:
            rows = self.fallback.impact_entries_for_advisor(advisor_id)
        return rows

    def impact_entry_for_recommendation(self, recommendation_id: str) -> dict | None:
        row = self._read("impact_entry_for_recommendation", lambda r: r.impact_entry_for_recommendation(recommendation_id))
        if not row and self.primary is not self.fallback:
            row = self.fallback.impact_entry_for_recommendation(recommendation_id)
        return row

    def all_impact_entries(self) -> list[dict]:
        rows = self._read("all_impact_entries", lambda r: r.all_impact_entries())
        if not rows and self.primary is not self.fallback:
            rows = self.fallback.all_impact_entries()
        return rows

    # --- rec status / transitions ---
    def get_rec_status(self, recommendation_id: str) -> str | None:
        val = self._read("get_rec_status", lambda r: r.get_rec_status(recommendation_id))
        if val is None and self.primary is not self.fallback:
            val = self.fallback.get_rec_status(recommendation_id)
        return val

    def set_rec_status(self, recommendation_id: str, status: str, note: str | None = None) -> None:
        self._both_write("set_rec_status", lambda r: r.set_rec_status(recommendation_id, status, note))

    def record_transition(self, transition: dict) -> None:
        self._both_write("record_transition", lambda r: r.record_transition(transition))

    def transitions_for(self, recommendation_id: str) -> list[dict]:
        rows = self._read("transitions_for", lambda r: r.transitions_for(recommendation_id))
        if not rows and self.primary is not self.fallback:
            rows = self.fallback.transitions_for(recommendation_id)
        return rows

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
