from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import config

def create_main_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in config.MAIN_MENU_BUTTONS:
        keyboard.row(*[KeyboardButton(btn) for btn in row])
    return keyboard

def create_models_menu(models: list) -> ReplyKeyboardMarkup:
    """Создает клавиатуру выбора моделей"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for model in models:
        keyboard.add(KeyboardButton(model['name']))
    keyboard.add(KeyboardButton("Назад"))
    return keyboard
