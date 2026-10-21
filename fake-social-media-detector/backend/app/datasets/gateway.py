"""Choose the dataset store. Temporary disk is never described as durable."""

from __future__ import annotations

import os

from app.datasets.sql_store import SqlDatasetStore, StorageUnavailable, is_postgres


def dataset_database_url() -> str:
    return os.environ.get("DATASET_DATABASE_URL", "").strip()


def build_store(paths: dict | None = None):
    url = dataset_database_url()
    on_vercel = bool(os.environ.get("VERCEL"))
    if url and is_postgres(url):
        return SqlDatasetStore(url)
    if url.startswith("sqlite") and os.environ.get("DATASET_ALLOW_SQLITE") == "1" and not on_vercel:
        return SqlDatasetStore(url)
    if on_vercel or url:
        raise StorageUnavailable(
            "Durable dataset storage is not configured. Set DATASET_DATABASE_URL to a PostgreSQL URL. Temporary disk is not used."
        )
    from app.datasets.collect import dataset_paths

    return _JsonlFacade(paths or dataset_paths())


class _JsonlFacade:
    """Development JSONL files. durable stays false."""

    def __init__(self, paths: dict) -> None:
        self.paths = paths
        self.durable = False
        self.backend = "local_jsonl"

    def list_page(self, *, platform: str = "", review: str = "", limit: int = 50, offset: int = 0) -> dict:
        from app.datasets.collect import list_observations

        payload = list_observations(self.paths, platform=platform, review=review)
        rows = payload["observations"]
        total = len(rows)
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        payload["observations"] = rows[offset : offset + limit]
        payload["page"] = {"limit": limit, "offset": offset, "total": total}
        return payload

    def detail(self, observation_id: str):
        from app.datasets.collect import observation_detail

        return observation_detail(self.paths, observation_id)

    def full_observation(self, observation_id: str):
        from app.datasets import _read_jsonl

        for row in _read_jsonl(self.paths["observations"]):
            if row.get("observation_id") == observation_id:
                return row
        return None

    def save_label(self, record: dict) -> str:
        from app.datasets import append_label

        result = append_label(self.paths["labels"], record)
        self.record_audit("review", record.get("account_key", ""), result)
        return result

    def delete_account(self, account_key: str) -> dict:
        from app.datasets import _read_jsonl, delete_account

        logins = {
            str(row.get("public_login") or "").lower()
            for row in _read_jsonl(self.paths["observations"])
            if row.get("account_key") == account_key
        }
        removed = delete_account(self.paths["observations"], self.paths["labels"], account_key)
        removed["log_removed"] = _drop_log(self.paths["log"], logins)
        self.record_audit("delete", account_key, "removed" if removed["observations_removed"] else "missing")
        return removed

    def export_text(self, fmt: str) -> str:
        from app.datasets.collect import export_documents

        return export_documents(self.paths, fmt)

    def record_audit(self, action: str, account_key: str, result: str) -> None:
        from app.datasets.collect import _append_log

        audit = self.paths.get("audit")
        if not audit:
            return
        _append_log(audit, [{"action": action, "input": account_key, "result": result, "public_login": ""}])

    def readiness_rows(self):
        from app.datasets import _read_jsonl

        observations = _read_jsonl(self.paths["observations"])
        labels = _read_jsonl(self.paths["labels"])
        return observations, labels

    def health(self) -> dict:
        page = self.list_page(limit=1)
        storage = page["summary"].get("storage") or {}
        return storage


def _drop_log(path, logins: set[str]) -> int:
    import json

    from app.datasets import _read_jsonl

    if not path.exists() or not logins:
        return 0
    rows = _read_jsonl(path)
    kept = []
    removed = 0
    for row in rows:
        login = str(row.get("public_login") or row.get("input") or "").lower()
        if login in logins:
            removed += 1
            continue
        kept.append(row)
    if removed:
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept), encoding="utf-8")
    return removed
