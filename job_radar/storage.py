"""存储层：SQLite，一个文件就是一份数据集。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import JobPosting

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       TEXT NOT NULL,
    title         TEXT NOT NULL,
    city          TEXT NOT NULL DEFAULT '',
    salary_min    INTEGER,
    salary_max    INTEGER,
    salary_months INTEGER NOT NULL DEFAULT 12,
    edu           TEXT NOT NULL DEFAULT '',
    exp           TEXT NOT NULL DEFAULT '',
    skills        TEXT NOT NULL DEFAULT '',
    source        TEXT NOT NULL DEFAULT '',
    url           TEXT NOT NULL DEFAULT '',
    raw_text      TEXT NOT NULL DEFAULT '',
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (company, title, city)
);
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs (city);
"""


def _to_row(job: JobPosting) -> tuple:
    return (
        job.company,
        job.title,
        job.city,
        job.salary_min,
        job.salary_max,
        job.salary_months,
        job.edu,
        job.exp,
        ",".join(job.skills),
        job.source,
        job.url,
        job.raw_text,
    )


def _from_row(row: sqlite3.Row) -> JobPosting:
    return JobPosting(
        company=row["company"],
        title=row["title"],
        city=row["city"],
        salary_min=row["salary_min"],
        salary_max=row["salary_max"],
        salary_months=row["salary_months"],
        edu=row["edu"],
        exp=row["exp"],
        skills=[s for s in row["skills"].split(",") if s],
        source=row["source"],
        url=row["url"],
        raw_text=row["raw_text"],
    )


class JobStore:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, job: JobPosting) -> bool:
        """插入一条；公司+职位+城市重复时跳过。返回是否真的插入。"""
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO jobs "
                "(company, title, city, salary_min, salary_max, salary_months, "
                " edu, exp, skills, source, url, raw_text) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                _to_row(job),
            )
            return cur.rowcount > 0

    def save_many(self, jobs: list[JobPosting]) -> int:
        return sum(1 for job in jobs if self.save(job))

    def all(self) -> list[JobPosting]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
        return [_from_row(r) for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])