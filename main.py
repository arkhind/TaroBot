from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logger.add("bot.log", format="{time} {level} {message}", level="INFO")

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Привет")

async def main():
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN не найден в .env')
        return
    logger.info('Бот запущен')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
