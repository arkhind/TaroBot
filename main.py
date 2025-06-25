import sys
import asyncio
from datetime import datetime
from loguru import logger
import uuid

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from mixpanel import Mixpanel

import config
from config import BOT_TOKEN, VOX_TOKEN
from keyboards import main_menu, get_name_keyboard
from vox_executable import process_user_nickname, process_user_nicknames
from db.User import User
from vox.asyncapi import AsyncVoxAPI
from translations.get_phrase import get_phrase
from utils.get_user_info import get_current_username, get_language
from utils.login_requied import only_registered, only_registered_callback
from utils.zodiac import get_zodiac_sign
from inline_daily_prediction import router as inline_router, VoxMiddleware
from typing import Union

# Загружаем промпты
from prompts import *


# FSM состояния
class BotStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_yes_no_question = State()
    waiting_for_comp_nick = State()
    waiting_for_qualities_nick = State()
    waiting_for_name = State()
    waiting_for_birth_date = State()


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
                distinct_id=str(callback.message.from_user.id),
                event_name="prediction",
                properties={
                    "telegram_user_id": callback.from_user.id,
                    "telegram_chat_id": callback.message.chat.id,
                    "user_id": db_user.user_id,
                },
            )
        try:
            report = await process_user_nickname(
                vox, get_current_username(callback), prediction_prompt
            )
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu)
            else:
                await loading.edit_text(
                    "Не удалось получить предсказание. Попробуйте позже.",
                    reply_markup=main_menu
                )
        except Exception as e:
            logger.exception(e)
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

    # Переходим к запросу даты рождения
    await callback.message.answer(
        get_phrase(phrase_tag="ask_birth_date", language=get_language(callback))
    )
    await state.set_state(BotStates.waiting_for_birth_date)


@dp.message(BotStates.waiting_for_name)
async def process_name_input(message: Message, state: FSMContext):
    # Если пользователь ввел имя текстом
    name = message.text.strip()
    if len(name) > 50:
        await message.answer("Имя слишком длинное. Попробуйте короче.")
        return

    await state.update_data(name=name)
    await message.answer(
        get_phrase(phrase_tag="ask_birth_date", language=get_language(message))
    )
    await state.set_state(BotStates.waiting_for_birth_date)


@dp.message(BotStates.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    try:
        assert message.from_user
        # Парсим дату в формате ДД.ММ.ГГГГ
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()

        # Получаем сохраненное имя
        data = await state.get_data()
        name = data.get("name", "Пользователь")

        # Определяем знак зодиака (получаем тег)
        zodiac_tag = get_zodiac_sign(birth_date)

        # Получаем перевод знака зодиака
        zodiac_sign = get_phrase(phrase_tag=zodiac_tag, language=get_language(message))

        # Сохраняем данные в БД
        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        user.name = name
        user.birth_date = birth_date
        user.zodiac_sign = zodiac_tag  # Сохраняем тег, а не перевод
        await user.aio_save()

        # Очищаем состояние
        await state.clear()

        user = await User.aio_get(
            telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
        )
        if mixpanel:
            mixpanel.track(
                distinct_id=str(message.from_user.id),
                event_name="finish_registration",
                properties={
                    "telegram_user_id": message.from_user.id,
                    "telegram_chat_id": message.chat.id,
                    "user_id": user.user_id,
                },
            )
        # Отправляем сообщение о завершении регистрации
        await message.answer(
            get_phrase(
                phrase_tag="registration_complete", language=get_language(message)
            ).replace("{zodiac_sign}", zodiac_sign)
        )
        logger.info(f"User registered {user.user_id}")

        # Показываем главное меню
        nickname = name
        await message.answer(
            get_phrase(phrase_tag="menu", language=get_language(message))
            .replace("{nickname}", nickname)
            .replace("{zodiac_sign}", zodiac_sign),
            reply_markup=main_menu,
        )

    except ValueError:
        await message.answer(
            "Неверный формат даты. Используйте формат ДД.ММ.ГГГГ (например, 15.03.1990)"
        )
    except Exception as e:
        logger.exception(e)
        await message.answer(
            "Произошла ошибка при сохранении данных. Попробуйте еще раз."
        )


@dp.message(BotStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
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
    try:
        prompt = f"Вопрос: {question}" + answers_prompt
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message)),
            reply_markup=main_menu
        )


@dp.message(BotStates.waiting_for_yes_no_question)
async def process_yes_no(message: Message, state: FSMContext):
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
    try:
        prompt = f"Вопрос: {question}" + yes_no_prompt
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message)),
            reply_markup=main_menu
        )


@dp.message(BotStates.waiting_for_comp_nick)
async def process_compatibility(message: Message, state: FSMContext):
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
    try:
        logger.info(f"[DEBUG] process_compatibility: вызываем process_user_nicknames с {user_nick} и {target[1:]}")
        report = await process_user_nicknames(
            vox, user_nick, target[1:], compatibility_prompt
        )
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu)
        else:
            logger.error(f"[DEBUG] process_compatibility: process_user_nicknames вернул None")
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже.",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.exception(f"[DEBUG] process_compatibility: ошибка при вызове process_user_nicknames: {e}")
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message)),
            reply_markup=main_menu
        )


@dp.message(BotStates.waiting_for_qualities_nick)
async def process_qualities(message: Message, state: FSMContext):
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
    try:
        logger.info(f"[DEBUG] process_qualities: вызываем process_user_nickname для получения качеств {target[1:]}")
        target_qualities = await process_user_nickname(
            vox, target[1:], qualities_prompt["people_qualities"]
        )  ## получаем качества target'а
        if target_qualities:
            logger.info(f"[DEBUG] process_qualities: качества получены, вызываем process_user_nicknames")
            report = await process_user_nicknames(
                vox,
                user_nick,
                target[1:],
                qualities_prompt["tips"].replace("{info}", target_qualities),
            )
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu)
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
        # report = await process_user_nicknames(
        #     vox, user_nick, target[1:], qualities_prompt
        # )
        # if report:
        #     await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
        # else:
        #     await loading.edit_text(
        #         "Не удалось получить предсказание. Попробуйте позже."
        #     )
    except Exception as e:
        logger.exception(f"[DEBUG] process_qualities: ошибка при обработке: {e}")
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message)), reply_markup=main_menu
        )


@dp.message()
@only_registered
async def fallback(message: Message, user_db: User):
    await message.answer("Пожалуйста, используйте кнопки меню (/menu).")


async def main():
    global bot, vox
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден")
        return

    # Инициализируем бота с поддержкой inline режима
    bot = Bot(
        token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    vox = AsyncVoxAPI(token=VOX_TOKEN)

    # Добавляем middleware для передачи vox в inline хендлеры
    inline_router.inline_query.middleware(VoxMiddleware(vox))
    inline_router.callback_query.middleware(VoxMiddleware(vox))

    # Регистрируем inline хендлеры в глобальный диспетчер
    dp.include_router(inline_router)

    # Запускаем бота
    logger.info(f"Бот запущен на {bot.id}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
