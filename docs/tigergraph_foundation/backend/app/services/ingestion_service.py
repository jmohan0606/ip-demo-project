from __future__ import annotations
import json
import threading
import uuid
from datetime import datetime, timezone
from .. import db
from ..config import settings
from .manifest_service import ManifestService
from .tigergraph_client import TigerGraphClient

_workers: dict[str, threading.Thread] = {}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

class IngestionService:
    def __init__(self):
        self.manifest = ManifestService()
        self.tg = TigerGraphClient()

    def validate(self, selected: list[str] | None = None) -> list[dict]:
        entries = self.manifest.resolve_selection(selected, include_dependencies=True)
        return [self.manifest.inspect(entry) for entry in entries]

    def start(self, selected: list[str] | None, skip_unchanged: bool, batch_size: int | None, mode: str = "LOAD") -> str:
        entries = self.manifest.resolve_selection(selected, include_dependencies=True)
        inspections = [self.manifest.inspect(entry) for entry in entries]
        invalid = [item for item in inspections if not item["valid"]]
        if invalid:
            raise ValueError(f"Cannot start ingestion: {len(invalid)} file(s) failed validation")
        run_id = str(uuid.uuid4())
        actual_batch_size = max(1, min(batch_size or settings.load_batch_size, 10000))
        total_rows = sum(item["actual_rows"] for item in inspections)
        config = {"skip_unchanged": skip_unchanged, "batch_size": actual_batch_size, "selected": selected or []}
        db.execute(
            "INSERT INTO ingestion_run(run_id,status,mode,started_at,total_files,total_rows,config_json,message) VALUES(?,?,?,?,?,?,?,?)",
            (run_id, "QUEUED", mode, now(), len(entries), total_rows, json.dumps(config), "Run queued"),
        )
        thread = threading.Thread(
            target=self._run,
            args=(run_id, entries, skip_unchanged, actual_batch_size),
            daemon=True,
        )
        _workers[run_id] = thread
        thread.start()
        return run_id

    def _run(self, run_id: str, entries: list[dict], skip_unchanged: bool, batch_size: int) -> None:
        db.execute("UPDATE ingestion_run SET status=?,message=? WHERE run_id=?", ("RUNNING", "Loading files", run_id))
        try:
            for entry in entries:
                if self._run_status(run_id) in {"PAUSED", "CANCELLED"}:
                    break
                self._load_file(run_id, entry, skip_unchanged, batch_size)
            status = self._run_status(run_id)
            if status not in {"PAUSED", "CANCELLED", "FAILED"}:
                failed = db.row("SELECT failed_rows FROM ingestion_run WHERE run_id=?", (run_id,))["failed_rows"]
                final_status = "COMPLETED" if failed == 0 else "COMPLETED_WITH_ERRORS"
                db.execute(
                    "UPDATE ingestion_run SET status=?,completed_at=?,message=? WHERE run_id=?",
                    (final_status, now(), "Load completed" if failed == 0 else "Load completed with row errors", run_id),
                )
        except Exception as exc:
            db.execute(
                "UPDATE ingestion_run SET status=?,completed_at=?,message=? WHERE run_id=?",
                ("FAILED", now(), str(exc), run_id),
            )

    def _load_file(self, run_id: str, entry: dict, skip_unchanged: bool, batch_size: int) -> None:
        info = self.manifest.inspect(entry)
        rel = entry["file"]
        existing = db.row("SELECT * FROM ingestion_file WHERE run_id=? AND file_path=?", (run_id, rel))
        start_row = int(existing["next_row_number"]) if existing else 1
        if not existing:
            db.execute(
                "INSERT INTO ingestion_file(run_id,file_path,target,kind,file_hash,status,total_rows,next_row_number,started_at,message) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (run_id, rel, entry["target"], entry["kind"], info["hash"], "RUNNING", info["actual_rows"], 1, now(), "Loading"),
            )
        else:
            db.execute(
                "UPDATE ingestion_file SET status=?,message=?,completed_at=NULL WHERE run_id=? AND file_path=?",
                ("RUNNING", f"Resuming at row {start_row}", run_id, rel),
            )

        previous = db.row("SELECT * FROM source_file_version WHERE file_path=?", (rel,))
        if start_row == 1 and skip_unchanged and previous and previous["file_hash"] == info["hash"]:
            db.execute(
                "UPDATE ingestion_file SET status=?,skipped_rows=?,processed_rows=?,next_row_number=?,completed_at=?,message=? WHERE run_id=? AND file_path=?",
                ("SKIPPED", info["actual_rows"], info["actual_rows"], info["actual_rows"] + 1, now(), "Unchanged file skipped", run_id, rel),
            )
            self._bump_run(run_id, processed=0, skipped=info["actual_rows"], file_done=True)
            return

        batch: list[dict] = []
        row_numbers: list[int] = []
        batch_no = max(0, (start_row - 1) // batch_size)
        for row_no, row in self.manifest.read_rows(entry, start_row=start_row):
            batch.append(row)
            row_numbers.append(row_no)
            if len(batch) >= batch_size:
                current_status = self._run_status(run_id)
                if current_status in {"PAUSED", "CANCELLED"}:
                    db.execute(
                        "UPDATE ingestion_file SET status=?,message=? WHERE run_id=? AND file_path=?",
                        (current_status, f"Stopped before row {row_numbers[0]}", run_id, rel),
                    )
                    return
                self._load_batch(run_id, entry, rel, batch_no, batch, row_numbers)
                batch, row_numbers = [], []
                batch_no += 1
        if batch:
            current_status = self._run_status(run_id)
            if current_status in {"PAUSED", "CANCELLED"}:
                db.execute(
                    "UPDATE ingestion_file SET status=?,message=? WHERE run_id=? AND file_path=?",
                    (current_status, f"Stopped before row {row_numbers[0]}", run_id, rel),
                )
                return
            self._load_batch(run_id, entry, rel, batch_no, batch, row_numbers)

        state = db.row("SELECT * FROM ingestion_file WHERE run_id=? AND file_path=?", (run_id, rel))
        status = "COMPLETED" if state and state["failed_rows"] == 0 else "COMPLETED_WITH_ERRORS"
        db.execute(
            "UPDATE ingestion_file SET status=?,completed_at=?,message=? WHERE run_id=? AND file_path=?",
            (status, now(), "File load complete", run_id, rel),
        )
        if status == "COMPLETED":
            db.execute(
                "INSERT OR REPLACE INTO source_file_version(file_path,file_hash,last_successful_run_id,last_loaded_at,row_count) VALUES(?,?,?,?,?)",
                (rel, info["hash"], run_id, now(), info["actual_rows"]),
            )
        self._bump_run(run_id, file_done=True)

    def _load_batch(self, run_id: str, entry: dict, rel: str, batch_no: int, batch: list[dict], row_numbers: list[int]) -> None:
        row_start, row_end = min(row_numbers), max(row_numbers)
        db.execute(
            "INSERT OR REPLACE INTO ingestion_batch(run_id,file_path,batch_no,row_start,row_end,status,requested_rows,started_at) VALUES(?,?,?,?,?,?,?,?)",
            (run_id, rel, batch_no, row_start, row_end, "RUNNING", len(batch), now()),
        )
        succeeded, errors, response_log = self._upsert_with_isolation(entry, batch, row_numbers)
        failed = len(errors)
        batch_status = "COMPLETED" if failed == 0 else "COMPLETED_WITH_ERRORS"
        db.execute(
            "UPDATE ingestion_batch SET status=?,succeeded_rows=?,failed_rows=?,completed_at=?,response_json=? WHERE run_id=? AND file_path=? AND batch_no=?",
            (batch_status, succeeded, failed, now(), json.dumps(response_log), run_id, rel, batch_no),
        )
        db.execute(
            "UPDATE ingestion_file SET processed_rows=processed_rows+?,succeeded_rows=succeeded_rows+?,failed_rows=failed_rows+?,last_successful_batch=?,next_row_number=? WHERE run_id=? AND file_path=?",
            (len(batch), succeeded, failed, batch_no, row_end + 1, run_id, rel),
        )
        self._bump_run(run_id, processed=len(batch), succeeded=succeeded, failed=failed)
        for row_no, row, error in errors:
            business_key = self._business_key(entry, row)
            db.execute(
                "INSERT INTO ingestion_row_error(run_id,file_path,batch_no,row_no,business_key,error_code,error_message,row_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (run_id, rel, batch_no, row_no, business_key, "UPSERT_FAILED", error, json.dumps(row), now()),
            )

    def _upsert_with_isolation(self, entry: dict, rows: list[dict], row_numbers: list[int]):
        try:
            response = self.tg.upsert(entry, rows)
            return len(rows), [], [{"rows": row_numbers, "response": response}]
        except Exception as exc:
            if len(rows) == 1:
                return 0, [(row_numbers[0], rows[0], str(exc))], [{"rows": row_numbers, "error": str(exc)}]
            middle = len(rows) // 2
            s1, e1, r1 = self._upsert_with_isolation(entry, rows[:middle], row_numbers[:middle])
            s2, e2, r2 = self._upsert_with_isolation(entry, rows[middle:], row_numbers[middle:])
            return s1 + s2, e1 + e2, r1 + r2

    @staticmethod
    def _business_key(entry: dict, row: dict) -> str:
        if entry["kind"] == "vertex":
            return str(row.get(entry["id_column"], ""))
        return f"{row.get(entry['from_column'],'')}->{row.get(entry['to_column'],'')}"

    def retry_failed(self, source_run_id: str, batch_size: int | None = None) -> str:
        failed = db.rows(
            "SELECT * FROM ingestion_row_error WHERE run_id=? AND resolved=0 ORDER BY file_path,row_no",
            (source_run_id,),
        )
        if not failed:
            raise ValueError("No unresolved row errors exist for this run")
        run_id = str(uuid.uuid4())
        grouped: dict[str, list[dict]] = {}
        for error in failed:
            grouped.setdefault(error["file_path"], []).append(error)
        total_rows = len(failed)
        config = {"retry_of_run_id": source_run_id, "batch_size": batch_size or settings.load_batch_size}
        db.execute(
            "INSERT INTO ingestion_run(run_id,status,mode,started_at,total_files,total_rows,retry_of_run_id,config_json,message) VALUES(?,?,?,?,?,?,?,?,?)",
            (run_id, "RUNNING", "RETRY_FAILED_ROWS", now(), len(grouped), total_rows, source_run_id, json.dumps(config), "Retrying failed rows"),
        )
        entries = self.manifest.entry_map()
        def worker():
            try:
                for file_path, error_rows in grouped.items():
                    entry = entries[file_path]
                    records = [json.loads(item["row_json"]) for item in error_rows]
                    numbers = [int(item["row_no"]) for item in error_rows]
                    db.execute(
                        "INSERT INTO ingestion_file(run_id,file_path,target,kind,status,total_rows,started_at,message) VALUES(?,?,?,?,?,?,?,?)",
                        (run_id, file_path, entry["target"], entry["kind"], "RUNNING", len(records), now(), "Retrying failed rows"),
                    )
                    succeeded, remaining, response = self._upsert_with_isolation(entry, records, numbers)
                    failed_count = len(remaining)
                    db.execute(
                        "UPDATE ingestion_file SET status=?,processed_rows=?,succeeded_rows=?,failed_rows=?,completed_at=?,message=? WHERE run_id=? AND file_path=?",
                        ("COMPLETED" if not remaining else "COMPLETED_WITH_ERRORS", len(records), succeeded, failed_count, now(), "Retry complete", run_id, file_path),
                    )
                    self._bump_run(run_id, processed=len(records), succeeded=succeeded, failed=failed_count, file_done=True)
                    succeeded_numbers = set(numbers) - {item[0] for item in remaining}
                    if succeeded_numbers:
                        placeholders = ",".join("?" for _ in succeeded_numbers)
                        db.execute(
                            f"UPDATE ingestion_row_error SET resolved=1 WHERE run_id=? AND file_path=? AND row_no IN ({placeholders})",
                            (source_run_id, file_path, *sorted(succeeded_numbers)),
                        )
                    for row_no, row, error in remaining:
                        db.execute(
                            "INSERT INTO ingestion_row_error(run_id,file_path,batch_no,row_no,business_key,error_code,error_message,row_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (run_id, file_path, 0, row_no, self._business_key(entry,row), "RETRY_FAILED", error, json.dumps(row), now()),
                        )
                state = db.row("SELECT failed_rows FROM ingestion_run WHERE run_id=?", (run_id,))
                final = "COMPLETED" if state and state["failed_rows"] == 0 else "COMPLETED_WITH_ERRORS"
                db.execute("UPDATE ingestion_run SET status=?,completed_at=?,message=? WHERE run_id=?", (final, now(), "Retry completed", run_id))
            except Exception as exc:
                db.execute("UPDATE ingestion_run SET status=?,completed_at=?,message=? WHERE run_id=?", ("FAILED", now(), str(exc), run_id))
        thread = threading.Thread(target=worker, daemon=True)
        _workers[run_id] = thread
        thread.start()
        return run_id

    def _bump_run(self, run_id: str, processed=0, succeeded=0, failed=0, skipped=0, file_done=False) -> None:
        db.execute(
            "UPDATE ingestion_run SET processed_rows=processed_rows+?,succeeded_rows=succeeded_rows+?,failed_rows=failed_rows+?,skipped_rows=skipped_rows+?,completed_files=completed_files+? WHERE run_id=?",
            (processed, succeeded, failed, skipped, 1 if file_done else 0, run_id),
        )

    def _run_status(self, run_id: str) -> str:
        result = db.row("SELECT status FROM ingestion_run WHERE run_id=?", (run_id,))
        return result["status"] if result else "UNKNOWN"

    def status(self, run_id: str):
        run = db.row("SELECT * FROM ingestion_run WHERE run_id=?", (run_id,))
        if not run:
            return None
        run["files"] = db.rows("SELECT * FROM ingestion_file WHERE run_id=? ORDER BY rowid", (run_id,))
        run["errors"] = db.rows(
            "SELECT * FROM ingestion_row_error WHERE run_id=? ORDER BY error_id DESC LIMIT 200", (run_id,)
        )
        denominator = run["total_rows"] or 0
        run["progress_pct"] = round(100 * (run["processed_rows"] + run["skipped_rows"]) / denominator, 2) if denominator else 100.0
        return run

    def list_runs(self, limit: int = 50):
        return db.rows("SELECT * FROM ingestion_run ORDER BY started_at DESC LIMIT ?", (limit,))

    def pause(self, run_id: str):
        db.execute(
            "UPDATE ingestion_run SET status=?,message=? WHERE run_id=? AND status IN ('QUEUED','RUNNING')",
            ("PAUSED", "Paused by user", run_id),
        )

    def resume(self, run_id: str) -> bool:
        old = self.status(run_id)
        if not old or old["status"] != "PAUSED":
            return False
        config = json.loads(old.get("config_json") or "{}")
        remaining_paths = [f["file_path"] for f in old["files"] if f["status"] not in {"COMPLETED", "SKIPPED"}]
        entries = [e for e in self.manifest.entries() if e["file"] in remaining_paths]
        db.execute("UPDATE ingestion_run SET status=?,message=? WHERE run_id=?", ("RUNNING", "Resume requested", run_id))
        thread = threading.Thread(
            target=self._run,
            args=(run_id, entries, bool(config.get("skip_unchanged", False)), int(config.get("batch_size", settings.load_batch_size))),
            daemon=True,
        )
        _workers[run_id] = thread
        thread.start()
        return True
