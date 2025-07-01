import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger
from db.User import User
from db import database
from config import BOT_TOKEN, VOX_TOKEN
from vox.asyncapi import AsyncVoxAPI
from vox_executable import process_user_nickname
from prompts import prediction_prompt
import re
import html
from keyboards import main_menu

def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_ * [ ] ( ) ~ ` > # + - = | { } . !'.replace(' ', '')
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

async def get_all_users():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: list(User.select()))

async def send_weekly_predictions():
    bot = Bot(token=BOT_TOKEN)
    vox = AsyncVoxAPI(token=VOX_TOKEN)
    try:
        users = await get_all_users()
        for user in users:
            if not user.telegram_user_id or not user.telegram_chat_id:
                continue
            try:
                user_info = await bot.get_chat(user.telegram_user_id)
                username = user_info.username
                if not username:
                    logger.warning(f"[WEEKLY] No Telegram username for user_id {user.telegram_user_id}")
                    continue
                logger.info(f"[WEEKLY] Sending prediction to @{username} ({user.telegram_user_id})")
                html_prompt = prediction_prompt + "\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>, <code>код</code>, <a href=\"https://t.me/{username}\">ссылка</a> и т.д. Не используй Markdown."
                report = await process_user_nickname(vox, username, html_prompt)
                if report:
                    safe_report = report
                    safe_username = html.escape(username)
                    safe_header = html.escape('🔮 Ваше предсказание на неделю для')
                    await bot.send_message(
                        user.telegram_chat_id,
                        f"{safe_header} @{safe_username}!\n\n{safe_report}",
                        parse_mode=ParseMode.HTML,
                        reply_markup=main_menu
                    )
                else:
                    logger.warning(f"[WEEKLY] No prediction for @{username}")
            except Exception as e:
                logger.exception(f"[WEEKLY] Error for user_id {user.telegram_user_id}: {e}")
            await asyncio.sleep(10)
    finally:
        await bot.session.close()
        await vox.session.close()

if __name__ == "__main__":
    asyncio.run(send_weekly_predictions()) 