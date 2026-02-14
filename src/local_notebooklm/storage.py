import sqlite3
from pathlib import Path
from typing import Iterable


class MetadataStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    title TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
                """
            )

    def upsert_document(self, doc_id: str, source_type: str, source_ref: str, title: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, source_type, source_ref, title)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  source_type=excluded.source_type,
                  source_ref=excluded.source_ref,
                  title=excluded.title
                """,
                (doc_id, source_type, source_ref, title),
            )

    def replace_chunks(self, doc_id: str, rows: Iterable[tuple[str, int, str]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.executemany(
                "INSERT INTO chunks (id, document_id, idx, text) VALUES (?, ?, ?, ?)",
                ((chunk_id, doc_id, idx, text) for chunk_id, idx, text in rows),
            )

    def list_documents(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, source_type, source_ref, title, created_at FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
