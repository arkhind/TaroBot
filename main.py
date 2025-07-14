import sys
import asyncio
from datetime import datetime
from loguru import logger
import uuid
import html
import traceback
import concurrent.futures
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from mixpanel import Mixpanel
import aiogram.exceptions
from vox.exceptions import ApiError, NotFoundError

import config
from config import BOT_TOKEN, VOX_TOKEN
from keyboards import main_menu, get_name_keyboard, get_zodiac_keyboard
from vox_executable import process_user_nickname, process_user_nicknames
from db.User import User
from vox.asyncapi import AsyncVoxAPI
from translations.get_phrase import get_phrase
from utils.get_user_info import get_current_username, get_language
from utils.login_requied import only_registered, only_registered_callback
from utils.zodiac import get_zodiac_sign
from inline_daily_prediction import router as inline_router, VoxMiddleware
from typing import Union
from send_weekly_prediction import send_weekly_predictions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Загружаем промпты
from prompts import (
    answers_prompt,
    yes_no_prompt,
    compatibility_prompt,
    qualities_prompt,
    prediction_prompt,
    daily_prediction_prompt,
    compatibility_of_2_prompt,
    answers_prompt_gpt,
    yes_no_prompt_gpt,
    compatibility_prompt_gpt,
    qualities_prompt_gpt,
    daily_prediction_prompt_gpt,
    compatibility_of_2_prompt_gpt,
)


# FSM состояния
class BotStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_yes_no_question = State()
    waiting_for_comp_nick = State()
    waiting_for_qualities_nick = State()
    waiting_for_name = State()
    waiting_for_zodiac = State()


# Инициализация бота и диспетчера с FSM
bot = None
vox = None
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO", colorize=True)
if config.MIXPANEL_TOKEN:
    mixpanel = Mixpanel(config.MIXPANEL_TOKEN)
else:
    mixpanel = None


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    assert message.from_user
    user, created = await User.aio_get_or_create(
        telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
    )
    nickname = message.from_user.username
    full_name = message.from_user.full_name

    if created:
        # Создали => новый пользователь - начинаем регистрацию
        await message.answer(
            get_phrase(
                phrase_tag="registration_welcome", language=get_language(message)
            )
        )
        await message.answer(
            get_phrase(phrase_tag="ask_name", language=get_language(message)),
            reply_markup=get_name_keyboard(nickname, full_name),
        )
        await state.set_state(BotStates.waiting_for_name)
    else:
        # Уже было создано => старый пользователь
        if user.name and user.birth_date:
            # Пользователь уже зарегистрирован
            await message.answer(
                get_phrase(phrase_tag="welcome_back", language=get_language(message))
            )

            if mixpanel:
                mixpanel.track(
                    distinct_id=str(message.from_user.id),
                    event_name="menu_open",
                    properties={
                        "telegram_user_id": message.from_user.id,
                        "telegram_chat_id": message.chat.id,
                        "user_id": user.user_id,
                    },
                )

            # Получаем знак зодиака
            zodiac_sign = (
                get_phrase(phrase_tag=user.zodiac_sign, language=get_language(message))
                if user.zodiac_sign
                else "Не указан"
            )

            await message.answer(
                get_phrase(phrase_tag="menu", language=get_language(message))
                .replace("{nickname}", nickname or user.name)
                .replace("{zodiac_sign}", zodiac_sign),
                reply_markup=main_menu,
            )
        else:
            # Пользователь есть в БД, но не завершил регистрацию
            await message.answer(
                get_phrase(phrase_tag="ask_name", language=get_language(message)),
                reply_markup=get_name_keyboard(nickname, full_name),
            )
            await state.set_state(BotStates.waiting_for_name)
@dp.message(Command("menu"))
@only_registered
async def menu_handler(message: Message, db_user: User):
    nickname = db_user.name

    if mixpanel:
        mixpanel.track(
            distinct_id=str(message.from_user.id),
            event_name="menu_open",
            properties={
                "telegram_user_id": message.from_user.id,
                "telegram_chat_id": message.chat.id,
                "user_id": db_user.user_id,
            },
        )

    # Получаем знак зодиака
    zodiac_sign = (
        get_phrase(phrase_tag=db_user.zodiac_sign, language=get_language(message))
        if db_user.zodiac_sign
        else "Не указан"
    )

    await message.answer(
        get_phrase(phrase_tag="menu", language=get_language(message))
        .replace("{nickname}", nickname or db_user.name)
        .replace("{zodiac_sign}", zodiac_sign),
        reply_markup=main_menu,
    )


@dp.callback_query(
    lambda c: c.data
    in ["answers", "yes_no", "compatibility", "qualities", "prediction"]
)
@only_registered_callback
async def handle_callback_query(
    callback: CallbackQuery, state: FSMContext, db_user: User
):
    logger.info(f"[CALLBACK] Нажата кнопка: {callback.data} от user_id={callback.from_user.id if callback.from_user else 'unknown'}")
    await callback.answer()
    nickname = db_user.name
    if not nickname:
        await callback.message.answer(
            get_phrase(phrase_tag="nickname_error", language=get_language(callback))
        )
        return

    if callback.data == "answers":
        await state.set_state(BotStates.waiting_for_question)
        await callback.message.answer("🔮 Задайте ваш вопрос:")
    elif callback.data == "yes_no":
        await state.set_state(BotStates.waiting_for_yes_no_question)
        await callback.message.answer("🔮 Задайте вопрос для Да/Нет:")
    elif callback.data == "compatibility":
        await state.set_state(BotStates.waiting_for_comp_nick)
        await callback.message.answer(
            "🔮 Отправьте аккаунт другого человека (@nickname):"
        )
    elif callback.data == "qualities":
        await state.set_state(BotStates.waiting_for_qualities_nick)
        await callback.message.answer(
            "🔮 Отправьте аккаунт другого человека (@nickname):"
        )
    elif callback.data == "prediction":
        # Прямое предсказание без доп. ввода
        loading = await callback.message.answer(
            get_phrase(phrase_tag="wait_vox_answer", language=get_language(callback))
        )
        await callback.message.bot.send_chat_action(
            callback.message.chat.id, ChatAction.TYPING
        )
        if mixpanel:
            mixpanel.track(
                distinct_id=str(callback.from_user.id),
                event_name="prediction",
                properties={
                    "telegram_user_id": callback.from_user.id,
                    "telegram_chat_id": callback.message.chat.id,
                    "user_id": db_user.user_id,
                },
            )
        try:
            report = await process_user_nickname(
                vox, get_current_username(callback), daily_prediction_prompt
            )
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=main_menu)
            else:
                await loading.edit_text(
                    "Не удалось получить предсказание. Попробуйте позже.",
                    reply_markup=main_menu
                )
        except Exception as e:
            logger.exception(e)
            import traceback
            error_text = (
                f"<b>❗️ Ошибка при предсказании (prediction callback):</b>\n"
                f"<b>Nickname:</b> {get_current_username(callback)}\n"
                f"<pre>{traceback.format_exc()}</pre>"
            )
            chat_id = os.getenv('ERROR_CHAT_ID')
            if chat_id:
                await callback.message.bot.send_message(chat_id, error_text)
            else:
                logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
            await loading.edit_text(
                get_phrase(
                    phrase_tag="processed_error", language=get_language(callback)
                ),
                reply_markup=main_menu
            )


@dp.callback_query(lambda c: c.data.startswith("name_"))
async def handle_name_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == "name_skip":
        name = "Пользователь"
    else:
        name = callback.data.replace("name_", "")

    # Сохраняем имя в состоянии
    await state.update_data(name=name)

    # Показываем клавиатуру выбора знака зодиака
    await callback.message.answer(
        get_phrase(phrase_tag="ask_zodiac_sign", language=get_language(callback)),
        reply_markup=get_zodiac_keyboard()
    )
    await state.set_state(BotStates.waiting_for_zodiac)


@dp.message(BotStates.waiting_for_name)
async def process_name_input(message: Message, state: FSMContext):
    try:
        name = message.text.strip()
        if len(name) > 50:
            await message.answer("Имя слишком длинное. Попробуйте короче.")
            return
        await state.update_data(name=name)
        await message.answer(
            get_phrase(phrase_tag="ask_zodiac_sign", language=get_language(message)),
            reply_markup=get_zodiac_keyboard()
        )
        await state.set_state(BotStates.waiting_for_zodiac)
    except Exception as e:
        logger.exception(f"[process_name_input] Unhandled error: {e}")
        import traceback
        error_text = f"<b>❗️ Ошибка при вводе имени в основном боте:</b>\n<pre>{traceback.format_exc()}</pre>"
        chat_id = os.getenv('ERROR_CHAT_ID')
        if chat_id:
            await message.bot.send_message(chat_id, error_text)
        else:
            logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
        # Fallback на GPT (можно не делать для имени, если не требуется)
        # raise


@dp.callback_query(lambda c: c.data.startswith("zodiac_"))
async def handle_zodiac_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Получаем выбранный знак зодиака (тег уже содержит zodiac_)
    zodiac_tag = callback.data
    
    # Получаем сохраненное имя
    data = await state.get_data()
    name = data.get("name", "Пользователь")

    # Получаем перевод знака зодиака
    zodiac_sign = get_phrase(phrase_tag=zodiac_tag, language=get_language(callback))

    # Сохраняем данные в БД
    user = await User.aio_get(
        telegram_user_id=callback.from_user.id, telegram_chat_id=callback.message.chat.id
    )
    user.name = name
    user.birth_date = None  # Больше не сохраняем дату рождения
    user.zodiac_sign = zodiac_tag  # Сохраняем полный тег
    await user.aio_save()

    # Очищаем состояние
    await state.clear()

    if mixpanel:
        mixpanel.track(
            distinct_id=str(callback.from_user.id),
            event_name="finish_registration",
            properties={
                "telegram_user_id": callback.from_user.id,
                "telegram_chat_id": callback.message.chat.id,
                "user_id": user.user_id,
            },
        )
    
    # Отправляем сообщение о завершении регистрации
    await callback.message.answer(
        get_phrase(
            phrase_tag="registration_complete", language=get_language(callback)
        ).replace("{zodiac_sign}", zodiac_sign)
    )
    logger.info(f"User registered {user.user_id}")

    # Показываем главное меню
    nickname = name
    await callback.message.answer(
        get_phrase(phrase_tag="menu", language=get_language(callback))
        .replace("{nickname}", nickname)
        .replace("{zodiac_sign}", zodiac_sign),
        reply_markup=main_menu,
    )


@dp.message(BotStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    try:
        user_nick = get_current_username(message)
        question = message.text.strip()
        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        await state.clear()
        loading = await message.answer(
            get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
        )
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if mixpanel:
            mixpanel.track(
                distinct_id=str(message.from_user.id),
                event_name="question",
                properties={
                    "telegram_user_id": message.from_user.id,
                    "telegram_chat_id": message.chat.id,
                    "user_id": user.user_id,
                },
            )
        prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
        prompt = f"Вопрос: {question}" + answers_prompt + prediction_html_instruction
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(f"[process_question] Unhandled error: {e}")
        import traceback
        error_text = f"<b>❗️ Ошибка при вопросе в основном боте:</b>\n<pre>{traceback.format_exc()}</pre>"
        chat_id = os.getenv('ERROR_CHAT_ID')
        if chat_id:
            await message.bot.send_message(chat_id, error_text)
        else:
            logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
        # Fallback на GPT
        try:
            from utils.openai_gpt import ask_gpt
            prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
            prompt = f"Вопрос: {question}" + answers_prompt_gpt + prediction_html_instruction
            loop = asyncio.get_running_loop()
            gpt_result = await loop.run_in_executor(None, ask_gpt, prompt)
            await message.answer(gpt_result, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        except Exception as gpt_e:
            logger.error(f"Ошибка при генерации ответа через GPT: {gpt_e}")
        # raise


@dp.message(BotStates.waiting_for_yes_no_question)
async def process_yes_no(message: Message, state: FSMContext):
    try:
        user_nick = get_current_username(message)
        question = message.text.strip()
        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        await state.clear()
        loading = await message.answer(
            get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
        )
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if mixpanel:
            mixpanel.track(
                distinct_id=str(message.from_user.id),
                event_name="yes_no_question",
                properties={
                    "telegram_user_id": message.from_user.id,
                    "telegram_chat_id": message.chat.id,
                    "user_id": user.user_id,
                },
            )
        prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
        prompt = f"Вопрос: {question}" + yes_no_prompt + prediction_html_instruction
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(f"[process_yes_no] Unhandled error: {e}")
        import traceback
        error_text = f"<b>❗️ Ошибка при вопросе Да/Нет в основном боте:</b>\n<pre>{traceback.format_exc()}</pre>"
        chat_id = os.getenv('ERROR_CHAT_ID')
        if chat_id:
            await message.bot.send_message(chat_id, error_text)
        else:
            logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
        # Fallback на GPT
        try:
            from utils.openai_gpt import ask_gpt
            prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
            prompt = f"Вопрос: {question}" + yes_no_prompt_gpt + prediction_html_instruction
            loop = asyncio.get_running_loop()
            gpt_result = await loop.run_in_executor(None, ask_gpt, prompt)
            await message.answer(gpt_result, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        except Exception as gpt_e:
            logger.error(f"Ошибка при генерации ответа через GPT: {gpt_e}")
        # raise


@dp.message(BotStates.waiting_for_comp_nick)
async def process_compatibility(message: Message, state: FSMContext):
    try:
        user_nick = get_current_username(message)
        target = message.text.strip()
        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        logger.info(f"[DEBUG] process_compatibility: user_nick = {user_nick}")
        logger.info(f"[DEBUG] process_compatibility: target = {target}")
        logger.info(f"[DEBUG] process_compatibility: target[1:] = {target[1:]}")
        if not target.startswith("@"):
            await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
            return
        if target[1:] == user_nick:
            await message.answer(
                "Нельзя указать свой же ник. Отправьте аккаунт другого человека вида @nickname."
            )
            return
        await state.clear()
        loading = await message.answer(
            get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
        )
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if mixpanel:
            mixpanel.track(
                distinct_id=str(message.from_user.id),
                event_name="compatibility",
                properties={
                    "telegram_user_id": message.from_user.id,
                    "telegram_chat_id": message.chat.id,
                    "user_id": user.user_id,
                },
            )
        logger.info(f"[DEBUG] process_compatibility: вызываем process_user_nicknames с {user_nick} и {target[1:]}")
        prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
        manual_prompt = (
        "Проанализируй совместимость этих людей между собой (тебе пишет @" + user_nick ").\n"
        "Опиши главные черты каждого из них.\n"
        "Дай конкретный ответ в процентах насколько люди совместимы.\n"
        "Текста должно быть немного, все должно быть лаконично.\n"
        "Главное чтобы было количество процентов совместимости.\n"
        "Дай ответ на русском языке.\n"
        "Используй стиль гадания на картах таро, упомяни карты совместимости.\n"
        "Ответ должен быть полезным и вдохновляющим.\n"
        "Используй эмодзи в меру для создания атмосферы.\n"
        "Не используй bullet list.\n"
        "Не используй теги <ul>, <ol>, <li>.\n"
        "Не ссылайся на активность человека в конкретных каналах и чатах.\n"
        "Оформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй <html> и <body> теги."
        )
        report = await process_user_nicknames(
            vox, user_nick, target[1:], manual_prompt
        )
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        else:
            logger.error(f"[DEBUG] process_compatibility: process_user_nicknames вернул None")
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(f"[process_compatibility] Unhandled error: {e}")
        import traceback
        error_text = f"<b>❗️ Ошибка при совместимости в основном боте:</b>\n<pre>{traceback.format_exc()}</pre>"
        chat_id = os.getenv('ERROR_CHAT_ID')
        if chat_id:
            await message.bot.send_message(chat_id, error_text)
        else:
            logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
        # Fallback на GPT
        try:
            from utils.openai_gpt import ask_gpt
            prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
            prompt = compatibility_prompt_gpt + prediction_html_instruction
            loop = asyncio.get_running_loop()
            gpt_result = await loop.run_in_executor(None, ask_gpt, prompt)
            await message.answer(gpt_result, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        except Exception as gpt_e:
            logger.error(f"Ошибка при генерации ответа через GPT: {gpt_e}")
        # raise


@dp.message(BotStates.waiting_for_qualities_nick)
async def process_qualities(message: Message, state: FSMContext):
    try:
        user_nick = get_current_username(message)
        target = message.text.strip()
        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        logger.info(f"[DEBUG] process_qualities: user_nick = {user_nick}")
        logger.info(f"[DEBUG] process_qualities: target = {target}")
        logger.info(f"[DEBUG] process_qualities: target[1:] = {target[1:]}")
        if not target.startswith("@"):
            await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
            return
        if target[1:] == user_nick:
            await message.answer(
                "Нельзя указать свой же ник. Отправьте аккаунт другого человека вида @nickname."
            )
            return
        await state.clear()
        loading = await message.answer(
            get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
        )
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if mixpanel:
            mixpanel.track(
                distinct_id=str(message.from_user.id),
                event_name="qualities",
                properties={
                    "telegram_user_id": message.from_user.id,
                    "telegram_chat_id": message.chat.id,
                    "user_id": user.user_id,
                },
            )
        logger.info(f"[DEBUG] process_qualities: вызываем process_user_nickname для получения качеств {target[1:]}")
        target_qualities = await process_user_nickname(
            vox, target[1:], qualities_prompt["people_qualities"]
        )  ## получаем качества target'а
        if target_qualities:
            logger.info(f"[DEBUG] process_qualities: качества получены, вызываем process_user_nicknames")
            prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
            report = await process_user_nicknames(
                vox,
                user_nick,
                target[1:],
                qualities_prompt["tips"].replace("{info}", target_qualities) + prediction_html_instruction,
            )
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=main_menu)
            else:
                logger.error(f"[DEBUG] process_qualities: process_user_nicknames вернул None")
                await loading.edit_text(
                    "Не удалось получить предсказание. Попробуйте позже.",
                    reply_markup=main_menu
                )
        else:
            logger.error(f"[DEBUG] process_qualities: process_user_nickname вернул None")
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(f"[process_qualities] Unhandled error: {e}")
        import traceback
        error_text = f"<b>❗️ Ошибка при анализе качеств в основном боте:</b>\n<pre>{traceback.format_exc()}</pre>"
        chat_id = os.getenv('ERROR_CHAT_ID')
        if chat_id:
            await message.bot.send_message(chat_id, error_text)
        else:
            logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
        # Fallback на GPT
        try:
            from utils.openai_gpt import ask_gpt
            prediction_html_instruction = '\n\nОформи ответ с помощью HTML-тегов <b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>. Не используй Markdown.'
            prompt = qualities_prompt_gpt["tips"] + prediction_html_instruction
            loop = asyncio.get_running_loop()
            gpt_result = await loop.run_in_executor(None, ask_gpt, prompt)
            await message.answer(gpt_result, parse_mode=ParseMode.HTML, reply_markup=main_menu)
        except Exception as gpt_e:
            logger.error(f"Ошибка при генерации ответа через GPT: {gpt_e}")
        # raise


@dp.message()
async def fallback(message: Message):
    if message.chat.type == "private":
        await message.answer("Пожалуйста, используйте кнопки меню (/menu).")


async def on_error(update, exception):
    logger.error(f"[on_error] {exception}")
    import traceback
    # Определяем контекст для инлайн-режима
    context = ""
    details = ""
    if hasattr(update, 'inline_query') and update.inline_query:
        context = "Ошибка в инлайн-режиме (inline_query)"
        details = f"\n<b>Текст запроса:</b> {getattr(update.inline_query, 'query', '')}"
    elif hasattr(update, 'callback_query') and update.callback_query:
        context = "Ошибка в инлайн-режиме (callback_query)"
        data = getattr(update.callback_query, 'data', '')
        user_id = getattr(getattr(update.callback_query, 'from_user', None), 'id', '')
        details = f"\n<b>Callback data:</b> {data}\n<b>User ID:</b> {user_id}"
    else:
        context = "Ошибка вне message-хендлеров (например, polling/callback)"
    error_text = f"<b>❗️ {context}:</b>{details}\n<pre>{traceback.format_exc()}</pre>"
    chat_id = os.getenv('ERROR_CHAT_ID')
    if chat_id:
        await message.bot.send_message(chat_id, error_text)
    else:
        logger.error('ERROR_CHAT_ID не найден, ошибка не отправлена в чат')
    return True


async def main():
    global bot, vox
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден")
        return

    # Планировщик рассылки
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(
        send_weekly_predictions,
        CronTrigger(day_of_week='mon', hour=7, minute=0),
        name="Weekly predictions"
    )
    scheduler.start()

    # Инициализируем бота с поддержкой inline режима
    bot = Bot(
        token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    vox = AsyncVoxAPI(token=VOX_TOKEN)

    # Добавляем middleware для передачи vox в inline хендлеры
    inline_router.inline_query.middleware(VoxMiddleware(vox))
    inline_router.callback_query.middleware(VoxMiddleware(vox))

    # Регистрируем inline хендлеры в глобальный диспетчер
    dp.include_router(inline_router)

    # Запускаем бота
    logger.info(f"Бот запущен на {bot.id}")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        on_error=on_error
    )


if __name__ == "__main__":
    asyncio.run(main())
