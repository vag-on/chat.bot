import logging
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import InputFile, ContentType
from pathlib import Path
from config import config
from database.crud import DatabaseManager
from utils.file_processing import file_processor
from utils.api import api_client
from utils.menu import create_main_menu

logger = logging.getLogger(__name__)


def setup_files(dp: Dispatcher):
    @dp.message_handler(content_types=ContentType.DOCUMENT)
    async def handle_document(message: types.Message):
        """Обработчик входящих файлов"""
        user = message.from_user
        doc = message.document

        try:
            # Проверка размера файла
            if doc.file_size > config.MAX_FILE_SIZE:
                return await message.answer(
                    f"⚠️ Файл слишком большой (максимум {config.MAX_FILE_SIZE // 1024 // 1024} МБ)"
                )

            # Сохранение файла
            file_info = await file_processor.save_file(
                file=await doc.get_file(),
                user_id=user.id,
                original_name=doc.file_name
            )

            if not file_info:
                return await message.answer("❌ Ошибка сохранения файла")

            # Получение выбранной модели
            with DatabaseManager() as db:
                user_model = db.get_user(user.id).model

            # Обработка файла
            await message.answer("🔄 Файл обрабатывается...")
            result = await file_processor.process_file(
                file_path=Path(file_info['path']),
                user_id=user.id,
                model=user_model
            )

            if not result:
                return await message.answer("❌ Ошибка обработки файла")

            # Отправка результата
            if result['type'] == 'file':
                await message.answer_document(
                    document=result['telegram_file'],
                    caption="✅ Результат обработки файла"
                )
            elif result['type'] == 'text':
                await message.answer(
                    f"📄 Результат обработки:\n\n{result['content']}",
                    reply_markup=create_main_menu()
                )

        except Exception as e:
            logger.error(f"File handling error: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла критическая ошибка при обработке файла")

    @dp.message_handler(Text(equals="Очистить файлы"))
    async def handle_clear_files(message: types.Message):
        """Очистка истории файлов пользователя"""
        try:
            with DatabaseManager() as db:
                db.cursor.execute("DELETE FROM files WHERE user_id = ?", (message.from_user.id,))
                count = db.cursor.rowcount

            await message.answer(
                f"✅ Удалено {count} файлов из истории",
                reply_markup=create_main_menu()
            )
        except Exception as e:
            logger.error(f"Clear files error: {str(e)}")
            await message.answer("❌ Ошибка очистки файлов")

    @dp.message_handler(commands=['my_files'])
    async def cmd_my_files(message: types.Message):
        """Показывает историю загруженных файлов"""
        try:
            with DatabaseManager() as db:
                files = db.cursor.execute('''
                    SELECT file_uid, original_name, processed, created_at 
                    FROM files 
                    WHERE user_id = ?
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', (message.from_user.id,)).fetchall()

            if not files:
                return await message.answer("📁 Вы еще не загружали файлов")

            response = ["📂 Последние 10 файлов:"]
            for file in files:
                status = "✅ Обработан" if file[2] else "🔄 В процессе"
                response.append(
                    f"▫️ {file[1]} ({status})\n"
                    f"<code>ID: {file[0]}</code>\n"
                    f"Дата: {file[3][:16]}"
                )

            await message.answer(
                "\n\n".join(response),
                parse_mode='HTML',
                reply_markup=create_main_menu()
            )
        except Exception as e:
            logger.error(f"Files history error: {str(e)}")
            await message.answer("❌ Ошибка получения истории файлов")
