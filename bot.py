from aiogram import Bot, Dispatcher
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error('BOT_TOKEN не найден в .env')
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logger.add("bot.log", format="{time} {level} {message}", level="INFO")
