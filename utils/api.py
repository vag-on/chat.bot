import requests
import logging
import os
from typing import Optional, Dict, List, Union
from pathlib import Path
from config import config
from database.models import File

logger = logging.getLogger(__name__)


class APIHandler:
    """Класс для взаимодействия с внешним API"""

    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.timeout = config.API_TIMEOUT
        self.max_file_size = config.MAX_FILE_SIZE
        self.headers = {
            "User-Agent": "TelegramBot/1.0",
            "Accept": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Базовый метод для выполнения HTTP-запросов"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None

    def send_chat_request(
            self,
            model: str,
            messages: List[Dict[str, str]],
            temperature: float = 0.7
    ) -> Optional[Dict]:
        """
        Отправляет запрос к чат-API
        :param model: Идентификатор модели
        :param messages: Список сообщений в формате {"role": "user|assistant", "content": "text"}
        :param temperature: Параметр креативности (0-1)
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }
        return self._make_request("POST", "chat/completions", json=payload)

    def process_file(
            self,
            file_path: Union[str, Path],
            model: str,
            options: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Обрабатывает файл через API
        :param file_path: Путь к файлу
        :param model: Идентификатор модели
        :param options: Дополнительные параметры обработки
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            logger.error(f"File size exceeds limit: {file_size} bytes")
            return None

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                data = {
                    'model': model,
                    'options': str(options) if options else ''
                }
                return self._make_request("POST", "file/process", files=files, data=data)
        except IOError as e:
            logger.error(f"File processing error: {str(e)}")
            return None

    def get_available_models(self) -> Optional[List[Dict]]:
        """Получает список доступных моделей из API"""
        response = self._make_request("GET", "models")
        return response.get('data') if response else None

    def check_api_status(self) -> bool:
        """Проверяет доступность API"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5,
                headers=self.headers
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_file_processing_result(self, task_id: str) -> Optional[Dict]:
        """Получает результат обработки файла по ID задачи"""
        return self._make_request("GET", f"tasks/{task_id}")

    def download_processed_file(self, file_url: str, save_path: Path) -> bool:
        """
        Скачивает обработанный файл
        :param file_url: URL файла от API
        :param save_path: Путь для сохранения файла
        """
        try:
            response = requests.get(file_url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            return False


# Синглтон экземпляр для использования в других модулях
api_client = APIHandler()
