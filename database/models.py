import sqlite3
from datetime import datetime
from typing import Optional
from pathlib import Path
from config import config


def create_tables(conn: sqlite3.Connection) -> None:
    """Создает все необходимые таблицы в базе данных"""

    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY NOT NULL,
            username TEXT,
            model TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS model_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS ai_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (group_id) REFERENCES model_groups(id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT CHECK(role IN ('user', 'assistant', 'system')) NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_uid TEXT NOT NULL UNIQUE,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            original_name TEXT,
            processed BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_context_user ON context(user_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_files_user ON files(user_id)
        """
    ]

    cursor = conn.cursor()
    for table in tables:
        cursor.execute(table)
    conn.commit()


def initialize_base_data(conn: sqlite3.Connection) -> None:
    """Заполняет базовые данные моделей и групп"""

    groups_and_models = {
        "GPT": ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini"],
        "Llama": ["llama-3-8b", "llama-3.2-90b", "llama-3.3-70b"],
        "Gemini": ["gemini-2.0-flash", "gemini-2.0-flash-thinking"],
        "Claude": ["claude-3.5-sonnet", "claude-3.7-sonnet"],
        "BlackboxAI": ["blackboxai", "blackboxai-pro"]
    }

    cursor = conn.cursor()

    # Очистка старых данных
    cursor.execute("DELETE FROM ai_models")
    cursor.execute("DELETE FROM model_groups")

    # Вставка новых данных
    for group_name, models in groups_and_models.items():
        cursor.execute(
            "INSERT INTO model_groups (name) VALUES (?)",
            (group_name,)
        )
        group_id = cursor.lastrowid

        for model_name in models:
            cursor.execute(
                """INSERT INTO ai_models (group_id, name)
                VALUES (?, ?)""",
                (group_id, model_name)
            )

    conn.commit()


def database_exists() -> bool:
    """Проверяет существование файла базы данных"""
    return Path(config.DB_NAME).exists()


def get_db_connection() -> sqlite3.Connection:
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(config.DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class BaseModel:
    """Базовый класс для моделей данных"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class User(BaseModel):
    """Модель пользователя"""

    def __init__(
            self,
            id: int,
            username: Optional[str] = None,
            model: Optional[str] = None,
            created_at: Optional[datetime] = None,
            last_activity: Optional[datetime] = None
    ):
        super().__init__(
            id=id,
            username=username,
            model=model,
            created_at=created_at,
            last_activity=last_activity
        )


class File(BaseModel):
    """Модель файла"""

    def __init__(
            self,
            id: int,
            user_id: int,
            file_uid: str,
            file_type: str,
            file_path: str,
            original_name: Optional[str] = None,
            processed: bool = False,
            created_at: Optional[datetime] = None
    ):
        super().__init__(
            id=id,
            user_id=user_id,
            file_uid=file_uid,
            file_type=file_type,
            file_path=file_path,
            original_name=original_name,
            processed=processed,
            created_at=created_at
        )
