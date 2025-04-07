from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters import Text
from database.crud import DatabaseManager
from utils.menu import create_main_menu, create_models_menu
from config import config


def setup_commands(dp: Dispatcher):
    @dp.message_handler(commands=['start', 'help'])
    async def cmd_start(message: types.Message):
        """Обработчик команд /start и /help"""
        with DatabaseManager() as db:
            db.create_user(message.from_user.id, message.from_user.username)

        await message.answer(
            "🤖 <b>Добро пожаловать в AI Chat Bot!</b>\n\n"
            "Выберите языковую модель из меню ниже:",
            reply_markup=create_main_menu(),
            parse_mode='HTML'
        )

    @dp.message_handler(Text(equals=config.MAIN_MENU_BUTTONS))
    async def handle_main_menu(message: types.Message):
        """Обработка кнопок главного меню"""
        if message.text == "Очистить контекст":
            return await handle_clear_context(message)

        with DatabaseManager() as db:
            models = db.get_models_by_group(message.text)

        if not models:
            return await message.answer("⚠️ Модели для этой группы не найдены")

        await message.answer(
            f"🔧 Выберите модель из группы <b>{message.text}</b>:",
            reply_markup=create_models_menu(models),
            parse_mode='HTML'
        )

    async def handle_clear_context(message: types.Message):
        """Очистка контекста диалога"""
        with DatabaseManager() as db:
            if db.clear_context(message.from_user.id):
                await message.answer("✅ История диалога успешно очищена!")
            else:
                await message.answer("⚠️ Не удалось очистить историю")

        await message.answer(
            "Главное меню:",
            reply_markup=create_main_menu()
        )

    @dp.message_handler(Text(equals="Назад"))
    async def cmd_back(message: types.Message):
        """Обработка кнопки 'Назад'"""
        await cmd_start(message)

    @dp.message_handler(lambda message: message.text in get_all_models())
    async def handle_model_selection(message: types.Message):
        """Обработка выбора конкретной модели"""
        model_name = message.text
        with DatabaseManager() as db:
            success = db.update_user_model(
                user_id=message.from_user.id,
                model=model_name
            )

        if success:
            response = (
                f"✅ Модель <b>{model_name}</b> успешно выбрана!\n\n"
                "Теперь вы можете начать общение. Просто напишите "
                "свой вопрос или отправьте файл."
            )
        else:
            response = "⚠️ Ошибка выбора модели. Попробуйте снова."

        await message.answer(
            response,
            reply_markup=create_main_menu(),
            parse_mode='HTML'
        )


def get_all_models() -> list:
    """Возвращает список всех доступных моделей"""
    with DatabaseManager() as db:
        groups = db.get_model_groups()
        return [
            model['name']
            for group in groups
            for model in db.get_models_by_group(group['name'])
        ]
