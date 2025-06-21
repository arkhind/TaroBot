from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from loguru import logger
from dotenv import load_dotenv
import os
import sys
import asyncio
from vox_example import process_user_nickname
from keyboards import main_menu

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

answers_prompt_ = "".join(open("prompts/answers_prompt.txt").readlines())
compatibility_prompt_ = "".join(open("prompts/compatibility_prompt.txt").readlines())
prediction_prompt_ = "".join(open("prompts/prediction_prompt.txt").readlines())
qualities_prompt_ = "".join(open("prompts/qualities_prompt.txt").readlines())
yes_no_prompt_ = "".join(open("prompts/yes_no_prompt.txt").readlines())

bot = None
dp = Dispatcher()
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO", colorize=True)

def get_current_username(message: Message | CallbackQuery) -> str | None:
    """
    Получает никнейм пользователя Telegram из объекта message или callback.
    """
    if isinstance(message, CallbackQuery):
        if message.from_user:
            return message.from_user.username
    elif isinstance(message, Message):
        if message.from_user:
            return message.from_user.username
    return None

@dp.message(CommandStart())
async def start_handler(message: Message):
    nickname = get_current_username(message)
    await message.answer(f"Опции:\nВаш никнейм: {nickname}", reply_markup=main_menu)

@dp.message(Command("совместимость"))
async def compatibility_handler(message: Message):
    await message.answer("Функция совместимости пока не реализована.")

@dp.callback_query()
async def handle_callback_query(callback: CallbackQuery):
    if not callback.message:
        await callback.answer("Ошибка: сообщение недоступно")
        return
        
    if callback.data == "answers":
        if answers_prompt_:
            nickname = get_current_username(callback)
            if not nickname:
                await callback.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
                return
            
            report = process_user_nickname(nickname, answers_prompt_)
            if report:
                await callback.message.answer(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await callback.message.answer("Не удалось получить ответ. Попробуйте позже.")
        else:
            await callback.message.answer("Функционал 'Ответы на вопросы' временно недоступен.")
    
    elif callback.data == "yes_no":
        if yes_no_prompt_:
            nickname = get_current_username(callback)
            if not nickname:
                await callback.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
                return
            
            report = process_user_nickname(nickname, yes_no_prompt_)
            if report:
                await callback.message.answer(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await callback.message.answer("Не удалось получить ответ. Попробуйте позже.")
        else:
            await callback.message.answer("Функционал 'Да/Нет' временно недоступен.")
    
    elif callback.data == "compatibility":
        if compatibility_prompt_:
            nickname = get_current_username(callback)
            if not nickname:
                await callback.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
                return
            
            report = process_user_nickname(nickname, compatibility_prompt_)
            if report:
                await callback.message.answer(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await callback.message.answer("Не удалось получить анализ совместимости. Попробуйте позже.")
        else:
            await callback.message.answer("Функционал 'Совместимость' временно недоступен.")
    
    elif callback.data == "prediction":
        if prediction_prompt_:
            nickname = get_current_username(callback)
            if not nickname:
                await callback.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
                return

            report = process_user_nickname(nickname, prediction_prompt_)
            if report:
                await callback.message.answer(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await callback.message.answer("Не удалось получить предсказание. Попробуйте позже.")
        else:
            await callback.message.answer("Функционал 'Предсказание на день' временно недоступен.")
    
    elif callback.data == "qualities":
        if qualities_prompt_:
            nickname = get_current_username(callback)
            if not nickname:
                await callback.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
                return
            
            report = process_user_nickname(nickname, qualities_prompt_)
            if report:
                await callback.message.answer(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await callback.message.answer("Не удалось получить анализ качеств. Попробуйте позже.")
        else:
            await callback.message.answer("Функционал 'Плохие и хорошие качества' временно недоступен.")
    
    await callback.answer()

@dp.message()
async def handle_buttons(message: Message):
    await message.answer("Пожалуйста, используйте кнопки меню для выбора функции.")

async def main():
    global bot
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN не найден в .env')
        return
    bot = Bot(token=BOT_TOKEN)
    logger.info('Бот запущен')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
