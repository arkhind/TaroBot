from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loguru import logger
from dotenv import load_dotenv
import os
import sys
import asyncio
from get_username import get_current_username
from vox_example import process_user_nickname

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = None
dp = Dispatcher()
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO", colorize=True)

@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Предсказание на день"),
                KeyboardButton(text="Да/Нет"),
                KeyboardButton(text="Плохие и хорошие качества")
            ]
        ],
        resize_keyboard=True
    )
    nickname = get_current_username(message)
    await message.answer(f"Опции:\nВаш никнейм: {nickname}", reply_markup=keyboard)

@dp.message(Command("совместимость"))
async def compatibility_handler(message: Message):
    await message.answer("Функция совместимости пока не реализована.")

@dp.message()
async def handle_buttons(message: Message):
    if message.text == "Да/Нет":
        user_id = message.from_user.id if message.from_user else None
        if user_id is not None:
            data = get_user_data(user_id)
            await message.answer(f"да\nДанные: {data}")
        else:
            await message.answer("Не удалось определить пользователя.")
    elif message.text == "Предсказание на день":
        nickname = get_current_username(message)
        if not nickname:
            await message.answer("Не удалось получить ваш никнейм. Пожалуйста, установите его в настройках Telegram.")
            return

        report = process_user_nickname(nickname)
        if report:
            formatted_report = report.replace('**', '*')
            await message.answer(formatted_report, parse_mode="Markdown")
        else:
            await message.answer("Не удалось получить предсказание. Попробуйте позже.")

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