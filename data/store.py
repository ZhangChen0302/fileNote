import json
import os
import sqlite3
import shutil
import datetime as dt
from loguru import logger

HOME = os.path.expanduser("~")
APPDATA_LOCAL = os.environ.get("LOCALAPPDATA", os.path.join(HOME, "AppData", "Local"))
DATA_DIR = os.path.join(APPDATA_LOCAL, "FileNote")
DB_PATH = os.path.join(DATA_DIR, "notes.db")
LEGACY_JSON = os.path.join(HOME, ".file_notes.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                note TEXT NOT NULL DEFAULT '',
                pinned INTEGER NOT NULL DEFAULT 0,
                favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            """
        )


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def migrate_json_if_needed():
    """若旧 JSON 存在且 SQLite 中无数据，则自动迁移并备份原文件。"""
    if not os.path.exists(LEGACY_JSON):
        return
    try:
        with connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            if count > 0:
                return

        with open(LEGACY_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return

        ts = _now()
        rows = []
        for path, note in data.items():
            if not isinstance(note, str):
                note = str(note)
            rows.append((os.path.normpath(path), note, ts, ts))

        with connect() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO notes(path, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
                rows,
            )

        # 备份旧文件
        backup = LEGACY_JSON + f".bak.{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(LEGACY_JSON, backup)
        logger.info("已迁移旧备注到 SQLite，并备份 JSON：{}", backup)
    except Exception:
        logger.exception("迁移旧 JSON 备注失败")
