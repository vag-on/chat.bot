import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import config
from database.crud import initialize_database
from handlers.commands import setup_commands
from handlers.files import setup_files
from handlers.messages import setup_messages

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Инициализация бота
        bot = Bot(token=config.API_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(bot, storage=storage)

        # Инициализация базы данных
        logger.info("Initializing database...")
        initialize_database()
        logger.info("Database initialized successfully")

        # Регистрация обработчиков
        logger.info("Registering handlers...")
        setup_commands(dp)
        setup_files(dp)
        setup_messages(dp)
        logger.info("Handlers registered successfully")

        # Запуск бота
        from aiogram.utils import executor
        logger.info("Starting bot...")
        executor.start_polling(dp, skip_updates=True)

    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
