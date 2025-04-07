from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from database.crud import DatabaseManager
from utils.api import api_client
from utils.menu import create_main_menu
from config import config


def setup_messages(dp: Dispatcher):
    @dp.message_handler(content_types=types.ContentType.TEXT)
    async def handle_text(message: types.Message):
        """Обработчик текстовых сообщений"""
        try:
            user = message.from_user

            # Получение контекста и модели
            with DatabaseManager() as db:
                context = db.get_context(user.id)
                user_model = db.get_user(user.id).model

            # Добавление нового сообщения в контекст
            context.append({"role": "user", "content": message.text})

            # Отправка запроса к API
            response = api_client.send_chat_request(
                model=user_model,
                messages=context[-config.MAX_CONTEXT_LENGTH:]
            )

            if not response or 'choices' not in response:
                return await message.answer("⚠️ Ошибка получения ответа")

            # Получение и сохранение ответа
            answer = response['choices'][0]['message']['content']
            with DatabaseManager() as db:
                db.add_message_to_context(user.id, "assistant", answer)

            # Отправка ответа пользователю
            await message.answer(
                answer,
                reply_markup=create_main_menu(),
                parse_mode='Markdown'
            )

        except Exception as e:
            logging.error(f"Message handling error: {str(e)}")
            await message.answer("❌ Произошла ошибка при обработке запроса")
