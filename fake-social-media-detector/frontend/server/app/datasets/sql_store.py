"""PostgreSQL dataset store. SQLite is accepted only for tests and is not durable."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, UniqueConstraint, create_engine, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import NullPool

from app.datasets.collect import partition_features, review_state


class StorageUnavailable(Exception):
    def __init__(self, message: str = "Dataset storage is unavailable.") -> None:
        super().__init__(message)
        self.message = message


class DatasetBase(DeclarativeBase):
    pass


class ObservationRow(DatasetBase):
    __tablename__ = "dataset_observations"

    observation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    account_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    public_login: Mapped[str] = mapped_column(String(80))
    observed_at: Mapped[str] = mapped_column(String(40))
    schema_version: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(40))
    model_status: Mapped[str] = mapped_column(String(40), default="")
    review_state: Mapped[str] = mapped_column(String(32), default="unreviewed", index=True)
    features_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40))


class LabelRow(DatasetBase):
    __tablename__ = "dataset_labels"
    __table_args__ = (UniqueConstraint("account_key", "label_type", "evidence_source", name="dataset_label_signature"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_key: Mapped[str] = mapped_column(String(64), index=True)
    observation_id: Mapped[str] = mapped_column(String(80), index=True)
    label_type: Mapped[str] = mapped_column(String(64))
    evidence_source: Mapped[str] = mapped_column(String(200))
    record_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40))


class LogRow(DatasetBase):
    __tablename__ = "dataset_collection_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_input: Mapped[str] = mapped_column(String(200), default="")
    result: Mapped[str] = mapped_column(String(40), default="")
    detail: Mapped[str] = mapped_column(String(300), default="")
    public_login: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[str] = mapped_column(String(40))


class AuditRow(DatasetBase):
    __tablename__ = "dataset_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(40))
    account_key: Mapped[str] = mapped_column(String(64), default="")
    result: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[str] = mapped_column(String(40))


def postgres_url(url: str) -> str:
    text_url = url.strip()
    if text_url.startswith("postgres://"):
        return "postgresql+psycopg://" + text_url[len("postgres://") :]
    if text_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + text_url[len("postgresql://") :]
    return text_url


def is_postgres(url: str) -> bool:
    normalized = postgres_url(url)
    return normalized.startswith("postgresql+psycopg://") or normalized.startswith("postgresql://")


class SqlDatasetStore:
    def __init__(self, url: str) -> None:
        self.url = postgres_url(url)
        self.durable = is_postgres(url)
        self.backend = "postgresql" if self.durable else "sqlite"
        self.mode = "production" if self.durable else "test"
        if self.url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            pool_kwargs = {}
        else:
            # One connection per use. Session and transaction poolers both reject a cached pool.
            connect_args = {"connect_timeout": 15, "prepare_threshold": None}
            pool_kwargs = {"poolclass": NullPool}
        try:
            self.engine = create_engine(self.url, connect_args=connect_args, pool_pre_ping=True, **pool_kwargs)
            DatasetBase.metadata.create_all(self.engine)
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise StorageUnavailable("Dataset storage is unavailable.") from exc

    @contextmanager
    def _session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def has_account(self, key: str) -> bool:
        with self._session() as session:
            found = session.scalar(select(ObservationRow.account_key).where(ObservationRow.account_key == key))
            return found is not None

    def save_observation(self, observation: dict) -> str:
        _reject_fabricated(observation)
        with self._session() as session:
            found = session.scalar(select(ObservationRow).where(ObservationRow.account_key == observation["account_key"]))
            if found is not None:
                session.add(_audit("collect", observation["account_key"], "duplicate"))
                return "duplicate"
            session.add(_observation_row(observation))
            session.add(_audit("collect", observation["account_key"], "stored"))
            return "stored"

    def add_results(self, results: list[dict]) -> None:
        with self._session() as session:
            for row in results:
                session.add(
                    LogRow(
                        entry_input=str(row.get("input") or "")[:200],
                        result=str(row.get("result") or "")[:40],
                        detail=str(row.get("detail") or "")[:300],
                        public_login=str(row.get("public_login") or "")[:80],
                        created_at=_now(),
                    )
                )

    def save_label(self, record: dict) -> str:
        signature = (
            record["account_key"],
            record["label_type"],
            str(record.get("evidence_source") or "").strip().lower(),
        )
        with self._session() as session:
            rows = session.scalars(select(LabelRow).where(LabelRow.account_key == signature[0])).all()
            for existing in rows:
                if (existing.account_key, existing.label_type, existing.evidence_source.strip().lower()) != signature:
                    continue
                previous = json.loads(existing.record_json)
                if previous.get("status") == "confirmed" and _canonical(previous) != _canonical(record):
                    session.add(_audit("review", signature[0], "kept_confirmed"))
                    return "kept_confirmed"
                session.add(_audit("review", signature[0], "duplicate"))
                return "duplicate"
            session.add(
                LabelRow(
                    account_key=signature[0],
                    observation_id=str(record.get("observation_id") or ""),
                    label_type=signature[1],
                    evidence_source=signature[2],
                    record_json=json.dumps(record, ensure_ascii=False),
                    created_at=_now(),
                )
            )
            observation = session.scalar(select(ObservationRow).where(ObservationRow.account_key == signature[0]))
            if observation is not None:
                labels = [_load_label(row) for row in rows] + [record]
                observation.review_state = review_state(labels)
            session.add(_audit("review", signature[0], "stored"))
            return "stored"

    def list_page(self, *, platform: str = "", review: str = "", limit: int = 50, offset: int = 0) -> dict:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        with self._session() as session:
            filters = []
            if platform:
                filters.append(ObservationRow.platform == platform)
            if review:
                filters.append(ObservationRow.review_state == review)
            count_stmt = select(func.count()).select_from(ObservationRow)
            row_stmt = select(ObservationRow)
            if filters:
                count_stmt = count_stmt.where(*filters)
                row_stmt = row_stmt.where(*filters)
            total = session.scalar(count_stmt) or 0
            rows = session.scalars(row_stmt.order_by(ObservationRow.observed_at).offset(offset).limit(limit)).all()
            page = [_public_observation(row) for row in rows]
            summary = self._summary(session)
        summary["page"] = {"limit": limit, "offset": offset, "total": total}
        return {"observations": page, "summary": summary, "page": summary["page"]}

    def detail(self, observation_id: str) -> dict | None:
        with self._session() as session:
            row = session.get(ObservationRow, observation_id)
            if row is None:
                return None
            labels = [
                _load_label(item)
                for item in session.scalars(select(LabelRow).where(LabelRow.account_key == row.account_key)).all()
            ]
            features = json.loads(row.features_json)
            return {
                "observation": _public_observation(row),
                "fields": partition_features(features),
                "reviews": [_public_label(item) for item in labels],
                "review_state": review_state(labels),
                "collection_is_not_a_label": True,
            }

    def full_observation(self, observation_id: str) -> dict | None:
        with self._session() as session:
            row = session.get(ObservationRow, observation_id)
            if row is None:
                return None
            return _full(row)

    def delete_account(self, account_key: str) -> dict:
        with self._session() as session:
            observations = session.scalars(select(ObservationRow).where(ObservationRow.account_key == account_key)).all()
            labels = session.scalars(select(LabelRow).where(LabelRow.account_key == account_key)).all()
            logins = {row.public_login.lower() for row in observations if row.public_login}
            logs = [row for row in session.scalars(select(LogRow)).all() if (row.public_login or row.entry_input).lower() in logins]
            for row in (*logs, *labels, *observations):
                session.delete(row)
            session.add(_audit("delete", account_key, "removed" if observations else "missing"))
            return {
                "observations_removed": len(observations),
                "labels_removed": len(labels),
                "log_removed": len(logs),
            }

    def iter_export(self, fmt: str):
        if fmt not in {"jsonl", "csv"}:
            raise ValueError("Export format must be jsonl or csv.")
        with Session(self.engine) as session:
            observations = session.scalars(select(ObservationRow).execution_options(yield_per=50))
            labels = []
            if fmt == "jsonl":
                for row in observations:
                    yield json.dumps({"record_type": "observation", **_export_observation(row)}, ensure_ascii=False) + "\n"
                for label in session.scalars(select(LabelRow).execution_options(yield_per=50)):
                    yield json.dumps({"record_type": "label", **_public_label(_load_label(label))}, ensure_ascii=False) + "\n"
                return
            header, lines = _csv_lines(observations)
            yield header
            for line in lines:
                yield line
            del labels

    def record_audit(self, action: str, account_key: str, result: str) -> None:
        with self._session() as session:
            session.add(_audit(action, account_key, result))

    def readiness_rows(self) -> tuple[list[dict], list[dict]]:
        with self._session() as session:
            observations = [
                {"account_key": row.account_key, "observed_at": row.observed_at}
                for row in session.scalars(select(ObservationRow)).all()
            ]
            labels = [_load_label(row) for row in session.scalars(select(LabelRow)).all()]
            return observations, labels

    def health(self) -> dict:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            healthy = True
            message = "Writes go to PostgreSQL." if self.durable else "SQLite is a test store. It is not production persistence."
        except Exception:
            healthy = False
            message = "Dataset storage is unavailable."
        return {
            "backend": self.backend,
            "durable": self.durable and healthy,
            "healthy": healthy,
            "mode": self.mode if healthy else "unavailable",
            "last_write_at": self._last_write(),
            "migration_status": "ready" if self.durable else "not_production",
            "message": message,
        }

    def _last_write(self) -> str | None:
        try:
            with self._session() as session:
                stamps = [row.created_at for row in session.scalars(select(AuditRow.created_at)).all() if row]
                return max(stamps) if stamps else None
        except Exception:
            return None

    def _summary(self, session: Session) -> dict:
        rows = session.scalars(select(ObservationRow)).all()
        labels = [_load_label(row) for row in session.scalars(select(LabelRow)).all()]
        logs = session.scalars(select(LogRow)).all()
        states = {"unreviewed": 0, "pending": 0, "confirmed": 0, "disagreement": 0, "unknown": 0}
        for row in rows:
            states[row.review_state] = states.get(row.review_state, 0) + 1
        label_counts: dict[str, int] = {}
        for row in labels:
            name = str(row.get("review_label") or row.get("label_type") or "unspecified")
            label_counts[name] = label_counts.get(name, 0) + 1
        stamps = sorted(row.observed_at for row in rows if row.observed_at)
        schemas = sorted({row.schema_version for row in rows if row.schema_version})
        platforms: dict[str, int] = {}
        for row in rows:
            platforms[row.platform] = platforms.get(row.platform, 0) + 1
        counts = {"stored": 0, "duplicate": 0, "duplicate_in_batch": 0, "invalid": 0, "error": 0, "not_attempted": 0}
        for row in logs:
            if row.result in counts:
                counts[row.result] += 1
        health = {
            "backend": self.backend,
            "durable": self.durable,
            "healthy": True,
            "mode": self.mode,
            "last_write_at": max((row.created_at for row in session.scalars(select(AuditRow)).all()), default=None),
            "migration_status": "ready" if self.durable else "not_production",
            "message": "Writes go to PostgreSQL." if self.durable else "SQLite is a test store. It is not production persistence.",
        }
        return {
            "observations": len(rows),
            "unique_accounts": len({row.account_key for row in rows}),
            "by_platform": platforms,
            "by_review_state": states,
            "by_label": label_counts,
            "unreviewed": states.get("unreviewed", 0),
            "unknown": states.get("unknown", 0),
            "collection_log": counts,
            "observed_from": stamps[0] if stamps else None,
            "observed_to": stamps[-1] if stamps else None,
            "schema_versions": schemas,
            "provenance_complete": sum(1 for row in rows if row.observation_id and row.source and row.schema_version and row.observed_at),
            "demos_included": False,
            "durable": self.durable,
            "storage_note": health["message"],
            "storage": health,
            "real_world_metrics": None,
        }


def _reject_fabricated(observation: dict) -> None:
    features = observation.get("features") or {}
    posts = features.get("posts") or {}
    likes = features.get("average_likes") or {}
    if posts.get("value") is not None or likes.get("value") is not None:
        raise ValueError("Refusing to store fabricated posts or likes.")


def _observation_row(observation: dict) -> ObservationRow:
    return ObservationRow(
        observation_id=observation["observation_id"],
        account_key=observation["account_key"],
        platform=str(observation.get("platform") or ""),
        public_login=str(observation.get("public_login") or ""),
        observed_at=str(observation.get("observed_at") or ""),
        schema_version=str(observation.get("schema_version") or ""),
        source=str(observation.get("source") or ""),
        model_status=str(observation.get("model_status") or ""),
        review_state="unreviewed",
        features_json=json.dumps(observation.get("features") or {}, ensure_ascii=False),
        created_at=_now(),
    )


def _audit(action: str, account_key: str, result: str) -> AuditRow:
    return AuditRow(action=action[:40], account_key=str(account_key or "")[:64], result=result[:40], created_at=_now())


def _load_label(row: LabelRow) -> dict:
    return json.loads(row.record_json)


def _public_label(record: dict) -> dict:
    keep = (
        "observation_id",
        "account_key",
        "platform",
        "public_login",
        "review_label",
        "label_type",
        "label_value",
        "status",
        "fact_kind",
        "harm",
        "evidence_source",
        "evidence_url",
        "evidence_collected_at",
        "reviewer",
        "reviewed_at",
        "rationale",
        "evidence_quality",
        "verification_method",
        "disagreement",
        "data_use",
    )
    return {key: record.get(key) for key in keep}


def _public_observation(row: ObservationRow) -> dict:
    return {
        "observation_id": row.observation_id,
        "account_key": row.account_key,
        "platform": row.platform,
        "public_login": row.public_login,
        "observed_at": row.observed_at,
        "schema_version": row.schema_version,
        "source": row.source,
        "review_state": row.review_state,
    }


def _full(row: ObservationRow) -> dict:
    return {**_public_observation(row), "model_status": row.model_status, "features": json.loads(row.features_json)}


def _export_observation(row: ObservationRow) -> dict:
    payload = _full(row)
    features = {}
    for name, field in payload["features"].items():
        status = field.get("status")
        features[name] = {"status": status, "value": None if status != "observed" else field.get("value")}
    payload["features"] = features
    return payload


def _csv_lines(rows) -> tuple[str, list[str]]:
    from app.datasets.collect import _csv

    documents = [_export_observation(row) for row in rows]
    text_body = _csv(documents)
    lines = text_body.splitlines(keepends=True)
    if not lines:
        return "", []
    return lines[0], lines[1:]


def _canonical(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
