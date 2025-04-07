import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from config import config
from database.models import User, File, get_db_connection, create_tables, initialize_base_data

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Класс для выполнения CRUD операций с базой данных"""

    def __init__(self):
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
            logger.error("Database error occurred", exc_info=True)
        else:
            self.conn.commit()
        self.conn.close()
        return True

    # ==================== Users ====================
    def create_user(self, user_id: int, username: Optional[str] = None) -> None:
        """Создает нового пользователя"""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
                (user_id, username)
            )
        except sqlite3.Error as e:
            logger.error(f"Error creating user: {e}")

    def get_user(self, user_id: int) -> Optional[User]:
        """Возвращает пользователя по ID"""
        try:
            self.cursor.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            user_data = self.cursor.fetchone()
            return User(**user_data) if user_data else None
        except sqlite3.Error as e:
            logger.error(f"Error getting user: {e}")
            return None

    def update_user_model(self, user_id: int, model: str) -> bool:
        """Обновляет выбранную модель пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET model = ? WHERE id = ?",
                (model, user_id)
            )
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating user model: {e}")
            return False

    # ==================== Models ====================
    def get_model_groups(self) -> List[Dict[str, Any]]:
        """Возвращает список групп моделей"""
        try:
            self.cursor.execute("SELECT * FROM model_groups")
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting model groups: {e}")
            return []

    def get_models_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        """Возвращает модели по названию группы"""
        try:
            self.cursor.execute('''
                SELECT ai_models.* 
                FROM ai_models
                JOIN model_groups ON ai_models.group_id = model_groups.id
                WHERE model_groups.name = ?
            ''', (group_name,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting models by group: {e}")
            return []

    # ==================== Context ====================
    def add_message_to_context(self, user_id: int, role: str, content: str) -> None:
        """Добавляет сообщение в контекст"""
        try:
            self.cursor.execute('''
                INSERT INTO context (user_id, role, content)
                VALUES (?, ?, ?)
            ''', (user_id, role, content))

            # Удаляем старые сообщения сверх лимита
            self.cursor.execute('''
                DELETE FROM context 
                WHERE id NOT IN (
                    SELECT id FROM context 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ) AND user_id = ?
            ''', (user_id, config.MAX_CONTEXT_LENGTH, user_id))
        except sqlite3.Error as e:
            logger.error(f"Error adding message to context: {e}")

    def get_context(self, user_id: int) -> List[Dict[str, Any]]:
        """Возвращает контекст пользователя"""
        try:
            self.cursor.execute('''
                SELECT role, content 
                FROM context 
                WHERE user_id = ? 
                ORDER BY timestamp ASC
            ''', (user_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting context: {e}")
            return []

    def clear_context(self, user_id: int) -> bool:
        """Очищает контекст пользователя"""
        try:
            self.cursor.execute(
                "DELETE FROM context WHERE user_id = ?",
                (user_id,)
            )
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error clearing context: {e}")
            return False

    # ==================== Files ====================
    def save_file(self, user_id: int, file_uid: str, file_type: str,
                  file_path: str, original_name: str) -> Optional[File]:
        """Сохраняет информацию о файле"""
        try:
            self.cursor.execute('''
                INSERT INTO files 
                (user_id, file_uid, file_type, file_path, original_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, file_uid, file_type, str(file_path), original_name))

            self.cursor.execute(
                "SELECT * FROM files WHERE id = ?",
                (self.cursor.lastrowid,)
            )
            file_data = self.cursor.fetchone()
            return File(**file_data) if file_data else None
        except sqlite3.Error as e:
            logger.error(f"Error saving file: {e}")
            return None

    def get_file_by_uid(self, file_uid: str) -> Optional[File]:
        """Возвращает файл по UID"""
        try:
            self.cursor.execute(
                "SELECT * FROM files WHERE file_uid = ?",
                (file_uid,)
            )
            file_data = self.cursor.fetchone()
            return File(**file_data) if file_data else None
        except sqlite3.Error as e:
            logger.error(f"Error getting file: {e}")
            return None

    def mark_file_processed(self, file_uid: str) -> bool:
        """Помечает файл как обработанный"""
        try:
            self.cursor.execute(
                "UPDATE files SET processed = 1 WHERE file_uid = ?",
                (file_uid,)
            )
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error marking file as processed: {e}")
            return False


def initialize_database():
    """Инициализирует базу данных при первом запуске"""
    if not Path(config.DB_NAME).exists():
        with DatabaseManager() as db:
            create_tables(db.conn)
            initialize_base_data(db.conn)
        logger.info("Database initialized successfully")
    else:
        logger.info("Database already exists")
