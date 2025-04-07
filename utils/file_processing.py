import os
import uuid
import logging
import shutil
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from aiogram import types
from aiogram.types import InputFile
from config import config
from database.crud import DatabaseManager
from utils.api import api_client

logger = logging.getLogger(__name__)


class FileProcessor:
    """Класс для обработки файловых операций"""

    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        self.max_file_size = config.MAX_FILE_SIZE
        self.allowed_types = config.ALLOWED_FILE_TYPES
        self._ensure_temp_dir()

    def _ensure_temp_dir(self) -> None:
        """Создает временную директорию при инициализации"""
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate_file_id(self) -> str:
        """Генерирует уникальный идентификатор файла"""
        return str(uuid.uuid4())

    async def save_file(
            self,
            file: types.File,
            user_id: int,
            original_name: str
    ) -> Optional[Dict]:
        """Сохраняет файл на диск и в базу данных"""
        try:
            file_id = self.generate_file_id()
            file_extension = original_name.split('.')[-1].lower()
            file_path = self.temp_dir / f"{file_id}.{file_extension}"

            # Скачивание файла
            await file.download_to_drive(file_path)

            # Проверка валидности файла
            if not self._validate_file(file_path):
                file_path.unlink(missing_ok=True)
                return None

            # Сохранение в базу данных
            with DatabaseManager() as db:
                file_data = db.save_file(
                    user_id=user_id,
                    file_uid=file_id,
                    file_type=file_extension,
                    file_path=str(file_path),
                    original_name=original_name
                )

            return {
                'id': file_data.id,
                'path': file_path,
                'uid': file_id,
                'type': file_extension
            }
        except Exception as e:
            logger.error(f"File saving error: {str(e)}")
            return None

    def _validate_file(self, file_path: Path) -> bool:
        """Проверяет файл на соответствие требованиям"""
        try:
            # Проверка размера файла
            if file_path.stat().st_size > self.max_file_size:
                logger.warning(f"File too large: {file_path}")
                return False

            # Проверка MIME-типа
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                logger.warning(f"Unknown file type: {file_path}")
                return False

            main_type = mime_type.split('/')[0]
            if main_type not in self.allowed_types:
                logger.warning(f"Unsupported file type: {mime_type}")
                return False

            return True
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False

    async def process_file(
            self,
            file_path: Path,
            user_id: int,
            model: str
    ) -> Optional[Dict]:
        """Обрабатывает файл через API"""
        try:
            # Отправка файла в API
            response = api_client.process_file(
                file_path=file_path,
                model=model,
                options={'user_id': user_id}
            )

            if not response or 'status' not in response:
                return None

            # Обработка разных типов ответов
            if response.get('file_url'):
                return await self._handle_file_response(response, user_id)
            elif response.get('text'):
                return {'type': 'text', 'content': response['text']}

            return None
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            return None

    async def _handle_file_response(
            self,
            response: Dict,
            user_id: int
    ) -> Optional[Dict]:
        """Обрабатывает ответ API с файлом"""
        try:
            file_url = response['file_url']
            original_name = response.get('original_name', 'processed_file')
            save_path = self.temp_dir / f"processed_{original_name}"

            # Скачивание файла
            if not api_client.download_processed_file(file_url, save_path):
                return None

            # Сохранение в базу данных
            with DatabaseManager() as db:
                file_data = db.save_file(
                    user_id=user_id,
                    file_uid=self.generate_file_id(),
                    file_type=save_path.suffix[1:],
                    file_path=str(save_path),
                    original_name=original_name,
                    processed=True
                )

            return {
                'type': 'file',
                'path': save_path,
                'original_name': original_name,
                'telegram_file': InputFile(save_path)
            }
        except Exception as e:
            logger.error(f"File response handling error: {str(e)}")
            return None

    def cleanup_temp_files(self, older_than_hours: int = 24) -> None:
        """Очищает временные файлы старше указанного времени"""
        try:
            now = datetime.now()
            for file in self.temp_dir.iterdir():
                if file.is_file():
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    if (now - file_time) > timedelta(hours=older_than_hours):
                        file.unlink()
                        logger.info(f"Deleted old file: {file.name}")
        except Exception as e:
            logger.error(f"Temp files cleanup error: {str(e)}")

    def get_file_mime_type(self, file_path: Path) -> Tuple[str, str]:
        """Определяет MIME-тип файла"""
        mime_type, encoding = mimetypes.guess_type(file_path)
        if not mime_type:
            return 'application', 'octet-stream'
        return mime_type.split('/')


# Глобальный экземпляр процессора файлов
file_processor = FileProcessor()
