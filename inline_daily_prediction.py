from aiogram import Router, F, Bot
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultUnion,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from loguru import logger
import re
import json
import html

from vox.asyncapi import AsyncVoxAPI
from vox_executable import process_user_nickname, process_user_nicknames
from prompts import (
    prediction_prompt,
    qualities_prompt,
    answers_prompt,
    yes_no_prompt,
    compatibility_prompt,
    compatibility_of_2_prompt,
    daily_prediction_prompt,
)
from utils.nickname_codec import encode_nickname, decode_nickname
from mixpanel import Mixpanel
from config import MIXPANEL_TOKEN

router = Router()
mp = Mixpanel(MIXPANEL_TOKEN) if MIXPANEL_TOKEN else None


def encode_nickname(nickname: str) -> str:
    """Кодирует никнейм для использования в callback_data, заменяя _ на -"""
    return nickname.replace("_", "-")


def decode_nickname(encoded_nickname: str) -> str:
    """Декодирует никнейм из callback_data, заменяя - на _"""
    return encoded_nickname.replace("-", "_")


def escape_nickname_for_markdown(nickname: str) -> str:
    """Экранирует никнейм для корректного отображения в Markdown"""
    return nickname.replace("_", "\\_")


class VoxMiddleware:
    def __init__(self, vox: AsyncVoxAPI):
        self.vox = vox

    async def __call__(self, handler, event, data):
        data["vox"] = self.vox
        return await handler(event, data)


@router.inline_query()
async def inline_prediction_handler(inline_query: InlineQuery, vox: AsyncVoxAPI):
    """Inline функция для обработки запросов"""
    results: list[InlineQueryResultUnion] = []
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id if inline_query.from_user else None
    logger.info(
        f"[INLINE] Получен запрос: '{query}' от user_id={user_id}"
    )
    query_type = 'nickname' if query.startswith("@") or (
        query and all(c.isalnum() or c == "_" for c in query) and len(query) < 30
    ) else 'question'
    
    if mp:
        mp.track(
            distinct_id=str(user_id) if user_id else "anonymous",
            event_name="inline_query",
            properties={
                "telegram_user_id": user_id,
                "query": query,
                "query_type": query_type
            },
        )

    if not query:
        logger.info("[INLINE] Пустой запрос, отправляю инструкцию")
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🔮 Введите никнейм или вопрос",
                description="Введите @nickname для предсказания, анализа качеств, совместимости или задайте вопрос",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "🔮 Введите @nickname для предсказания, анализа качеств или совместимости.\n"
                        "Задайте вопрос для получения ответа или выберите Да/Нет.\n\n"
                        "Доступные опции через кнопки после выбора:\n"
                        "• Получить предсказание\n"
                        "• Анализировать качества\n"
                        "• Совместимость с вами\n"
                        "• Ответ на вопрос\n"
                        "• Ответ Да/Нет\n"
                    )
                ),
            )
        ]
        await inline_query.answer(results=results, cache_time=1)
        return

    # Проверка на два никнейма через пробел
    match = re.match(r"@?(\w{1,30})\s+@?(\w{1,30})$", query)
    if match:
        nick1, nick2 = match.group(1), match.group(2)
        encoded_nick1 = encode_nickname(nick1)
        encoded_nick2 = encode_nickname(nick2)
        results = [
            InlineQueryResultArticle(
                id=f"compat2_{encoded_nick1}_{encoded_nick2}",
                title=f"❤️ Совместимость @{nick1} и @{nick2}",
                description="Узнать совместимость между двумя людьми",
                input_message_content=InputTextMessageContent(
                    message_text=f"❤️ Совместимость @{nick1} и @{nick2}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Совместимость двух людей",
                                callback_data=f"get_comp2_{encoded_nick1}_{encoded_nick2}",
                            )
                        ]
                    ]
                ),
            )
        ]
        logger.info(
            f"[INLINE] Кнопка совместимости двух людей: {results[0].reply_markup.inline_keyboard if results[0].reply_markup else None}"
        )
        await inline_query.answer(results=results, cache_time=1)
        return

    is_nickname = query.startswith("@") or (
        query and all(c.isalnum() or c == "_" for c in query) and len(query) < 30
    )
    logger.info(f"[INLINE] Тип запроса: {'никнейм' if is_nickname else 'вопрос'}")

    if is_nickname:
        clean_nickname = query[1:] if query.startswith("@") else query
        encoded_nickname = encode_nickname(clean_nickname)
        # Получаем ник отправителя (username или user_id)
        user_nick = (
            inline_query.from_user.username
            if inline_query.from_user and inline_query.from_user.username
            else str(inline_query.from_user.id) if inline_query.from_user else "user"
        )
        encoded_user_nick = encode_nickname(user_nick)
        results = [
            InlineQueryResultArticle(
                id=f"prediction_{encoded_nickname}",
                title=f"🔮 Предсказание для @{clean_nickname}",
                description="Получить предсказание на день",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔮 Предсказание на день для @{clean_nickname}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Получить предсказание",
                                callback_data=f"get_pred_{encoded_nickname}",
                            )
                        ]
                    ]
                ),
            ),
            InlineQueryResultArticle(
                id=f"qualities_{encoded_nickname}",
                title=f"🔍 Анализ качеств @{clean_nickname}",
                description="Анализировать качества и получить советы",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔍 Анализ качеств @{clean_nickname}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Анализировать качества",
                                callback_data=f"get_qual_{encoded_nickname}",
                            )
                        ]
                    ]
                ),
            ),
            InlineQueryResultArticle(
                id=f"compat2_{encoded_user_nick}_{encoded_nickname}",
                title=f"❤️ Совместимость @{user_nick} и @{clean_nickname}",
                description="Узнать совместимость между вами и этим человеком",
                input_message_content=InputTextMessageContent(
                    message_text=f"❤️ Совместимость @{user_nick} и @{clean_nickname}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Совместимость двух людей",
                                callback_data=f"get_comp2_{encoded_user_nick}_{encoded_nickname}",
                            )
                        ]
                    ]
                ),
            ),
        ]
        for r in results:
            if r.reply_markup and hasattr(r.reply_markup, "inline_keyboard"):
                logger.info(
                    f"[INLINE] Кнопки для никнейма: {r.reply_markup.inline_keyboard}"
                )
            else:
                logger.info(f"[INLINE] reply_markup: {r.reply_markup}")
    else:
        results = [
            InlineQueryResultArticle(
                id="question",
                title="🔮 Ответ на вопрос",
                description="Нажмите, чтобы получить ответ на ваш вопрос",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔮 Вопрос: {query}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Получить ответ",
                                callback_data=f"get_q_{query[:50]}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Получить ответ да/нет",
                                callback_data=f"get_yesno_{query[:50]}",
                            )
                        ],
                    ]
                ),
            )
        ]
    await inline_query.answer(results=results, cache_time=1)


@router.callback_query(lambda c: c.data.startswith("get_pred_"))
async def handle_get_prediction(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    nickname = decode_nickname(callback.data.replace("get_pred_", "")) if callback.data else ""
    logger.info(f"[CALLBACK] Получение предсказания для @{nickname}")
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_prediction",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "target_nickname": nickname
            },
        )
    
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>🔮 Получаем предсказание для @{nickname}...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>🔮 Получаем предсказание для @{nickname}...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        daily_prompt = daily_prediction_prompt
        prediction = await process_user_nickname(vox, nickname, daily_prompt)
        if prediction:
            formatted = f"<b>🔮 Предсказание на день для @{nickname}</b>\n\n{prediction}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить предсказание. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(
            f"[CALLBACK] Ошибка при получении предсказания для @{nickname}: {e}"
        )
        error_text = "❌ Произошла ошибка при получении предсказания."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_q_"))
async def handle_get_question(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    question = callback.data.replace("get_q_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение ответа на вопрос: {question}")
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_question",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "question": question[:100]  # Ограничиваем длину вопроса
            },
        )
    
    bot = callback.bot
    user_nick = (
        callback.from_user.username
        if callback.from_user and callback.from_user.username
        else str(callback.from_user.id) if callback.from_user else "user"
    )
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>🔮 Получаем ответ на вопрос...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>🔮 Получаем ответ на вопрос...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        question_prompt = f"Вопрос: {question}" + answers_prompt
        answer = await process_user_nickname(vox, user_nick, question_prompt)
        if answer:
            formatted = f"<b>🔮 Вопрос:</b> {question}\n\n<b>Ответ:</b>\n{answer}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить ответ. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении ответа на вопрос: {e}")
        error_text = "❌ Произошла ошибка при получении ответа."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_qual_"))
async def handle_get_qualities(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    nickname = decode_nickname(callback.data.replace("get_qual_", "")) if callback.data else ""
    logger.info(f"[CALLBACK] Получение анализа качеств для @{nickname}")
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_qualities",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "target_nickname": nickname
            },
        )
    
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>🔮 Анализируем качества @{nickname}...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>🔮 Анализируем качества @{nickname}...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        result = await process_user_nickname(
            vox, nickname, qualities_prompt["people_qualities"]
        )
        if result:
            formatted = f"<b>🔮 Анализ качеств @{nickname}</b>\n\n{result}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось проанализировать качества. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении анализа качеств для @{nickname}: {e}")
        error_text = "❌ Произошла ошибка при анализе качеств."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_yesno_"))
async def handle_get_yesno(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    question = callback.data.replace("get_yesno_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение ответа да/нет на вопрос: {question}")
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_yesno",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "question": question[:100]  # Ограничиваем длину вопроса
            },
        )
    
    bot = callback.bot
    user_nick = (
        callback.from_user.username
        if callback.from_user and callback.from_user.username
        else str(callback.from_user.id) if callback.from_user else "user"
    )
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>🔮 Получаем ответ Да/Нет...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>🔮 Получаем ответ Да/Нет...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        yesno_prompt_full = (
            f"Вопрос: {question}\n\nДай ответ Да или Нет с подробным объяснением."
            + yes_no_prompt
        )
        answer = await process_user_nickname(vox, user_nick, yesno_prompt_full)
        if answer:
            formatted = f"<b>🔮 Вопрос:</b> {question}\n\n<b>Ответ Да/Нет:</b>\n{answer}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить ответ. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении ответа да/нет: {e}")
        error_text = "❌ Произошла ошибка при получении ответа Да/Нет."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_comp_"))
async def handle_get_compatibility(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    target_nick = decode_nickname(callback.data.replace("get_comp_", "")) if callback.data else ""
    user_nick = callback.from_user.username if callback.from_user and callback.from_user.username else str(callback.from_user.id) if callback.from_user else "user"
    logger.info(f"[CALLBACK] Получение совместимости @{user_nick} и @{target_nick}")
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_compatibility",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "user_nickname": user_nick,
                "target_nickname": target_nick
            },
        )
    
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>❤️ Анализируем совместимость @{user_nick} и @{target_nick}...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>❤️ Анализируем совместимость @{user_nick} и @{target_nick}...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        report = await process_user_nicknames(vox, user_nick, target_nick, compatibility_prompt)
        if report:
            formatted = f"<b>❤️ Совместимость @{user_nick} и @{target_nick}</b>\n\n{report}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(formatted, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.HTML)
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить совместимость. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(error_text, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.HTML)
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении совместимости @{user_nick} и @{target_nick}: {e}")
        error_text = "❌ Произошла ошибка при анализе совместимости."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(error_text, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.HTML)
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_comp2_"))
async def handle_get_compatibility_two(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    data = callback.data.replace("get_comp2_", "") if callback.data else ""
    parts = data.split("_")
    if len(parts) >= 2:
        nick1 = decode_nickname(parts[0])
        nick2 = decode_nickname(parts[1])
    else:
        nick1, nick2 = data, ""
    logger.info(f"[CALLBACK] Получение совместимости двух людей: @{nick1} и @{nick2}")
    manual_prompt = (
        "Проанализируй совместимость этих людей между собой.\n"
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
    
    if mp:
        mp.track(
            distinct_id=str(callback.from_user.id) if callback.from_user else "anonymous",
            event_name="inline_compatibility_two",
            properties={
                "telegram_user_id": callback.from_user.id if callback.from_user else None,
                "nickname1": nick1,
                "nickname2": nick2
            },
        )
    
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"<b>❤️ Анализируем совместимость @{nick1} и @{nick2}...</b>\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"<b>❤️ Анализируем совместимость @{nick1} и @{nick2}...</b>\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
        report = await process_user_nicknames(vox, nick1, nick2, manual_prompt)
        if report:
            formatted = f"<b>❤️ Совместимость @{nick1} и @{nick2}</b>\n\n{report}"
            try:
                if callback.inline_message_id and bot is not None:
                    await bot.edit_message_text(
                        formatted,
                        inline_message_id=callback.inline_message_id,
                        parse_mode=ParseMode.HTML,
                    )
                elif callback.message and hasattr(callback.message, "edit_text"):
                    await callback.message.edit_text(formatted, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
            except Exception as e:
                logger.exception(f"[CALLBACK] Ошибка парсинга HTML, пробуем без parse_mode: {e}")
                # Пробуем отправить без parse_mode
                if callback.inline_message_id and bot is not None:
                    await bot.edit_message_text(
                        formatted,
                        inline_message_id=callback.inline_message_id
                    )
                elif callback.message and hasattr(callback.message, "edit_text"):
                    await callback.message.edit_text(formatted)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить совместимость. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.HTML,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении совместимости двух людей @{nick1} и @{nick2}: {e}")
        error_text = "❌ Произошла ошибка при анализе совместимости."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.HTML,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.HTML)  # type: ignore[attr-defined]
