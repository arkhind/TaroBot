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

from vox.asyncapi import AsyncVoxAPI
from vox_executable import process_user_nickname, process_user_nicknames
from prompts import (
    prediction_prompt,
    qualities_prompt,
    answers_prompt,
    yes_no_prompt,
    compatibility_prompt,
)

router = Router()


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
    logger.info(
        f"[INLINE] Получен запрос: '{query}' от user_id={inline_query.from_user.id if inline_query.from_user else 'unknown'}"
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
        results = [
            InlineQueryResultArticle(
                id=f"compat2_{nick1}_{nick2}",
                title=f"❤️ Совместимость @{nick1} и @{nick2}",
                description="Узнать совместимость между двумя людьми",
                input_message_content=InputTextMessageContent(
                    message_text=f"❤️ **Совместимость @{nick1} и @{nick2}**\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.MARKDOWN,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Совместимость двух людей",
                                callback_data=f"get_comp2_{nick1}_{nick2}",
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
        results = [
            InlineQueryResultArticle(
                id=f"prediction_{clean_nickname}",
                title=f"🔮 Предсказание для @{clean_nickname}",
                description="Получить предсказание на день",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔮 **Предсказание на день для @{clean_nickname}**\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.MARKDOWN,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Получить предсказание",
                                callback_data=f"get_pred_{clean_nickname}",
                            )
                        ]
                    ]
                ),
            ),
            InlineQueryResultArticle(
                id=f"qualities_{clean_nickname}",
                title=f"🔍 Анализ качеств @{clean_nickname}",
                description="Анализировать качества и получить советы",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔍 **Анализ качеств @{clean_nickname}**\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.MARKDOWN,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Анализировать качества",
                                callback_data=f"get_qual_{clean_nickname}",
                            )
                        ]
                    ]
                ),
            ),
            InlineQueryResultArticle(
                id=f"compat_{clean_nickname}",
                title=f"❤️ Совместимость с @{clean_nickname}",
                description="Узнать совместимость с этим человеком",
                input_message_content=InputTextMessageContent(
                    message_text=f"❤️ **Совместимость с @{clean_nickname}**\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.MARKDOWN,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Совместимость",
                                callback_data=f"get_comp_{clean_nickname}",
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
                    message_text=f"🔮 **Вопрос:** {query}\n\n⏳ Ожидайте...\n\nНажмите кнопку ниже, чтобы получить результат.",
                    parse_mode=ParseMode.MARKDOWN,
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
    nickname = callback.data.replace("get_pred_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение предсказания для @{nickname}")
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"🔮 **Получаем предсказание для @{nickname}...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"🔮 **Получаем предсказание для @{nickname}...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        daily_prompt = (
            f"""
Предсказание на день для пользователя с никнеймом: {nickname}

Создай подробное предсказание на сегодняшний день для этого человека. 
Включи в предсказание:
- Общий настрой дня
- Возможные события и встречи
- Советы на день
- Что стоит делать, а чего избегать
- Энергетический прогноз

Сделай предсказание позитивным и мотивирующим, но реалистичным.
"""
            + prediction_prompt
        )
        prediction = await process_user_nickname(vox, nickname, daily_prompt)
        if prediction:
            formatted = f"🔮 **Предсказание на день для @{nickname}**\n\n{prediction}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить предсказание. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(
            f"[CALLBACK] Ошибка при получении предсказания для @{nickname}: {e}"
        )
        error_text = "❌ Произошла ошибка при получении предсказания."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_q_"))
async def handle_get_question(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    question = callback.data.replace("get_q_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение ответа на вопрос: {question}")
    bot = callback.bot
    user_nick = (
        callback.from_user.username
        if callback.from_user and callback.from_user.username
        else str(callback.from_user.id) if callback.from_user else "user"
    )
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"🔮 **Получаем ответ на вопрос...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"🔮 **Получаем ответ на вопрос...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        question_prompt = f"Вопрос: {question}" + answers_prompt
        answer = await process_user_nickname(vox, user_nick, question_prompt)
        if answer:
            formatted = f"🔮 **Вопрос:** {question}\n\n**Ответ:**\n{answer}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить ответ. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении ответа на вопрос: {e}")
        error_text = "❌ Произошла ошибка при получении ответа."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_qual_"))
async def handle_get_qualities(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    nickname = callback.data.replace("get_qual_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение анализа качеств для @{nickname}")
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"🔮 **Анализируем качества @{nickname}...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"🔮 **Анализируем качества @{nickname}...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        target_qualities = await process_user_nickname(
            vox, nickname, qualities_prompt["people_qualities"]
        )
        if target_qualities:
            user_id = str(callback.from_user.id) if callback.from_user else "user"
            advice_prompt = qualities_prompt["tips"].replace("{info}", target_qualities)
            advice = await process_user_nicknames(vox, user_id, nickname, advice_prompt)
            if advice:
                formatted = f"🔮 **Анализ качеств @{nickname}**\n\n**Качества:**\n{target_qualities}\n\n**Советы для взаимодействия:**\n{advice}"
            else:
                formatted = f"🔮 **Анализ качеств @{nickname}**\n\n**Качества:**\n{target_qualities}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось проанализировать качества. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при анализе качеств @{nickname}: {e}")
        error_text = "❌ Произошла ошибка при анализе качеств."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_yesno_"))
async def handle_get_yesno(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    question = callback.data.replace("get_yesno_", "") if callback.data else ""
    logger.info(f"[CALLBACK] Получение ответа да/нет на вопрос: {question}")
    bot = callback.bot
    user_nick = (
        callback.from_user.username
        if callback.from_user and callback.from_user.username
        else str(callback.from_user.id) if callback.from_user else "user"
    )
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"🔮 **Получаем ответ Да/Нет...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"🔮 **Получаем ответ Да/Нет...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        yesno_prompt_full = (
            f"Вопрос: {question}\n\nДай ответ Да или Нет с подробным объяснением."
            + yes_no_prompt
        )
        answer = await process_user_nickname(vox, user_nick, yesno_prompt_full)
        if answer:
            formatted = f"🔮 **Вопрос:** {question}\n\n**Ответ Да/Нет:**\n{answer}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить ответ. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении ответа да/нет: {e}")
        error_text = "❌ Произошла ошибка при получении ответа Да/Нет."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_comp_"))
async def handle_get_compatibility(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    target_nick = callback.data.replace("get_comp_", "") if callback.data else ""
    user_nick = callback.from_user.username if callback.from_user and callback.from_user.username else str(callback.from_user.id) if callback.from_user else "user"
    logger.info(f"[CALLBACK] Получение совместимости @{user_nick} и @{target_nick}")
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"❤️ **Анализируем совместимость @{user_nick} и @{target_nick}...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"❤️ **Анализируем совместимость @{user_nick} и @{target_nick}...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        # Используем тот же промпт, что и для двух никнеймов
        comp2_prompt = (
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
            "Не ссылайся на активность человека в конкретных каналах и чатах.\n"
            "Отвечай на русском языке."
        )
        prompt = f"Пользователь 1: {user_nick}\nПользователь 2: {target_nick}\n\n" + comp2_prompt
        logger.info(f"[PROMPT] Итоговый prompt:\n{prompt}")
        report = await process_user_nicknames(vox, user_nick, target_nick, prompt)
        if report:
            formatted = f"❤️ **Совместимость @{user_nick} и @{target_nick}**\n\n{report}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(formatted, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.MARKDOWN)
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить совместимость. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(error_text, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.MARKDOWN)
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(f"[CALLBACK] Ошибка при получении совместимости @{user_nick} и @{target_nick}: {e}")
        error_text = "❌ Произошла ошибка при анализе совместимости."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(error_text, inline_message_id=callback.inline_message_id, parse_mode=ParseMode.MARKDOWN)
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]


@router.callback_query(lambda c: c.data.startswith("get_comp2_"))
async def handle_get_compatibility_two(callback: CallbackQuery, vox: AsyncVoxAPI):
    await callback.answer()
    data = callback.data.replace("get_comp2_", "") if callback.data else ""
    parts = data.split("_")
    if len(parts) >= 2:
        nick1, nick2 = parts[0], parts[1]
    else:
        nick1, nick2 = data, ""
    logger.info(f"[CALLBACK] Получение совместимости двух людей: @{nick1} и @{nick2}")
    bot = callback.bot
    try:
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                f"❤️ **Анализируем совместимость @{nick1} и @{nick2}...**\n\n⏳ Пожалуйста, подождите...",
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(f"❤️ **Анализируем совместимость @{nick1} и @{nick2}...**\n\n⏳ Пожалуйста, подождите...", parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        comp2_prompt = (
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
            "Не ссылайся на активность человека в конкретных каналах и чатах.\n"
            "Отвечай на русском языке."
        )
        prompt = f"Пользователь 1: {nick1}\nПользователь 2: {nick2}\n\n" + comp2_prompt
        logger.info(f"[PROMPT] Итоговый prompt:\n{prompt}")
        report = await process_user_nicknames(vox, nick1, nick2, prompt)
        if report:
            formatted = f"❤️ **Совместимость @{nick1} и @{nick2}**\n\n{report}"
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    formatted,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
        else:
            error_text = "❌ Не удалось получить совместимость. Попробуйте позже."
            if callback.inline_message_id and bot is not None:
                await bot.edit_message_text(
                    error_text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
    except Exception as e:
        logger.exception(
            f"[CALLBACK] Ошибка при получении совместимости двух людей @{nick1} и @{nick2}: {e}"
        )
        error_text = "❌ Произошла ошибка при анализе совместимости."
        if callback.inline_message_id and bot is not None:
            await bot.edit_message_text(
                error_text,
                inline_message_id=callback.inline_message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)  # type: ignore[attr-defined]
