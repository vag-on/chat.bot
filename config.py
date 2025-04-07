import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()


# Базовые настройки приложения
class Config:
    # Токен Telegram бота
    API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Настройки файловой системы
    BASE_DIR = Path(__file__).parent.resolve()
    TEMP_DIR = BASE_DIR / 'temp_files'
    os.makedirs(TEMP_DIR, exist_ok=True)  # Создаем папку при инициализации

    # Настройки базы данных
    DB_NAME = BASE_DIR / 'database' / 'database.db'
    DB_TIMEOUT = 30  # В секундах

    # Настройки API
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://145.255.12.37:1337/v1')
    API_TIMEOUT = 30  # В секундах

    # Лимиты для файлов
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    ALLOWED_FILE_TYPES = [
        'txt', 'pdf', 'doc', 'docx',
        'xls', 'xlsx', 'png', 'jpg', 'jpeg'
    ]

    # Настройки контекста
    MAX_CONTEXT_LENGTH = 20  # Количество сообщений
    CONTEXT_DAYS_TTL = 3  # Дней хранения контекста

    # Клавиатуры
    MAIN_MENU_BUTTONS = [
        ["GPT", "Llama"],
        ["Gemini", "Claude"],
        ["BlackboxAI", "Очистить контекст"]
    ]


# Инициализация конфига
config = Config()

# Проверка обязательных параметров
if not config.API_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in .env file")

if not config.API_BASE_URL:
    raise ValueError("API_BASE_URL must be set in .env file")
