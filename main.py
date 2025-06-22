import sys
import asyncio
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, VOX_TOKEN
from keyboards import main_menu
from vox_executable import process_user_nickname, process_user_nicknames
from db.User import User
from vox.asyncapi import AsyncVoxAPI
from translations.get_phrase import get_phrase
from utils.get_user_info import get_current_username, get_language
from utils.login_requied import only_registered

# Загружаем промпты
from prompts import *


# FSM состояния
class BotStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_yes_no_question = State()
    waiting_for_comp_nick = State()
    waiting_for_qualities_nick = State()


# Инициализация бота и диспетчера с FSM
bot = None
vox = None
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO", colorize=True)


@dp.message(CommandStart())
async def start_handler(message: Message):
    assert message.from_user
    user, created = await User.aio_get_or_create(
        telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
    )
    nickname = message.from_user.username
    if created:
        ...
        # Создали => новый пользователь
    else:
        ...
        # Уже было создано => старый пользователь
    await message.answer(
        get_phrase(phrase_tag="menu", language=get_language(message)).replace(
            '{nickname}', nickname
        ),
        reply_markup=main_menu,
    )


@dp.callback_query(
    lambda c: c.data
    in ["answers", "yes_no", "compatibility", "qualities", "prediction"]
)
async def handle_callback_query(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    nickname = get_current_username(callback)
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
        try:
            report = await process_user_nickname(vox, nickname, prediction_prompt)
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await loading.edit_text(
                    "Не удалось получить предсказание. Попробуйте позже."
                )
        except Exception as e:
            logger.exception(e)
            await loading.edit_text(
                get_phrase(
                    phrase_tag="processed_error", language=get_language(callback)
                )
            )


@dp.message(BotStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    question = message.text.strip()
    await state.clear()
    loading = await message.answer(
        get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        prompt = f"Вопрос: {question}" + answers_prompt
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже."
            )
    except Exception as e:
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message))
        )


@dp.message(BotStates.waiting_for_yes_no_question)
async def process_yes_no(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    question = message.text.strip()
    await state.clear()
    loading = await message.answer(
        get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        prompt = f"Вопрос: {question}" + yes_no_prompt
        report = await process_user_nickname(vox, user_nick, prompt)
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже."
            )
    except Exception as e:
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message))
        )


@dp.message(BotStates.waiting_for_comp_nick)
async def process_compatibility(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    target = message.text.strip()
    if not target.startswith("@"):
        await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
        return
    await state.clear()
    loading = await message.answer(
        get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        report = await process_user_nicknames(
            vox, user_nick, target[1:], compatibility_prompt
        )
        if report:
            await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже."
            )
    except Exception as e:
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message))
        )


@dp.message(BotStates.waiting_for_qualities_nick)
async def process_qualities(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    target = message.text.strip()
    if not target.startswith("@"):
        await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
        return
    await state.clear()
    loading = await message.answer(
        get_phrase(phrase_tag="wait_vox_answer", language=get_language(message))
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        target_qualities = await process_user_nickname(
            vox, target[1:], qualities_prompt["people_qualities"]
        )  ## получаем качества target'а
        if target_qualities:
            report = await process_user_nicknames(
                vox,
                user_nick,
                target[1:],
                qualities_prompt["tips"].replace('{info}', target_qualities),
            )
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await loading.edit_text(
                    "Не удалось получить предсказание. Попробуйте позже."
                )
        else:
            await loading.edit_text(
                "Не удалось получить предсказание. Попробуйте позже."
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
        logger.exception(e)
        await loading.edit_text(
            get_phrase(phrase_tag="processed_error", language=get_language(message))
        )


@dp.message()
async def fallback(message: Message):
    await message.answer("Пожалуйста, используйте кнопки меню.")


async def main():
    global bot, vox
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден")
        return
    bot = Bot(token=BOT_TOKEN)
    vox = AsyncVoxAPI(token=VOX_TOKEN)
    logger.info(f"Бот запущен на {bot.id}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
