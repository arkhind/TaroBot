from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from config import BOT_TOKEN
import sys
import asyncio
from vox_executable import process_user_nickname, process_user_nicknames
from keyboards import main_menu

# Загружаем промпты
answers_prompt_ = open("prompts/answers_prompt.txt").read()
yes_no_prompt_ = open("prompts/yes_no_prompt.txt").read()
compatibility_prompt_ = open("prompts/compatibility_prompt.txt").read()
qualities_prompt_ = open("prompts/qualities_prompt.txt").read()
prediction_prompt_ = open("prompts/prediction_prompt.txt").read()

# FSM состояния
class BotStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_yes_no_question = State()
    waiting_for_comp_nick = State()
    waiting_for_qualities_nick = State()

# Инициализация бота и диспетчера с FSM
bot = None
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO", colorize=True)

# Утилита для получения никнейма

def get_current_username(message: Message | CallbackQuery) -> str | None:
    if isinstance(message, (Message, CallbackQuery)) and message.from_user:
        return message.from_user.username
    return None

@dp.message(CommandStart())
async def start_handler(message: Message):
    nickname = get_current_username(message)
    await message.answer(f"Опции:\nВаш никнейм: {nickname}", reply_markup=main_menu)

@dp.callback_query(lambda c: c.data in ["answers", "yes_no", "compatibility", "qualities", "prediction"])
async def handle_callback_query(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    nickname = get_current_username(callback)
    if not nickname:
        await callback.message.answer("Не удалось получить ваш никнейм. Установите его в настройках Telegram.")
        return

    if callback.data == "answers":
        await state.set_state(BotStates.waiting_for_question)
        await callback.message.answer("🔮 Задайте ваш вопрос:")
    elif callback.data == "yes_no":
        await state.set_state(BotStates.waiting_for_yes_no_question)
        await callback.message.answer("🔮 Задайте вопрос для Да/Нет:")
    elif callback.data == "compatibility":
        await state.set_state(BotStates.waiting_for_comp_nick)
        await callback.message.answer("🔮 Отправьте аккаунт другого человека (@nickname):")
    elif callback.data == "qualities":
        await state.set_state(BotStates.waiting_for_qualities_nick)
        await callback.message.answer("🔮 Отправьте аккаунт другого человека (@nickname):")
    elif callback.data == "prediction":
        # Прямое предсказание без доп. ввода
        await callback.message.bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
        loading = await callback.message.answer("🔮 Тусую колоду 🔮")
        try:
            report = process_user_nickname(nickname, prediction_prompt_)
            if report:
                await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
            else:
                await loading.edit_text("Не удалось получить предсказание. Попробуйте позже.")
        except Exception as e:
            logger.error(e)
            await loading.edit_text(f"Произошла ошибка: {e}")

@dp.message(BotStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    question = message.text.strip()
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    loading = await message.answer("🔮 Тусую колоду 🔮")
    try:
        prompt = f"Вопрос: {question}" + answers_prompt_
        report = process_user_nickname(user_nick, prompt)
        await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(e)
        await loading.edit_text(f"Произошла ошибка: {e}")

@dp.message(BotStates.waiting_for_yes_no_question)
async def process_yes_no(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    question = message.text.strip()
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    loading = await message.answer("🔮 Тусую колоду 🔮")
    try:
        prompt = f"Вопрос: {question}" + yes_no_prompt_
        report = process_user_nickname(user_nick, prompt)
        await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(e)
        await loading.edit_text(f"Произошла ошибка: {e}")

@dp.message(BotStates.waiting_for_comp_nick)
async def process_compatibility(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    target = message.text.strip()
    if not target.startswith("@"):
        await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
        return
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    loading = await message.answer("🔮 Тусую колоду 🔮")
    try:
        report = process_user_nicknames(user_nick, target[1:], compatibility_prompt_)
        await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(e)
        await loading.edit_text("Карты Таро не знают ничего об этом человеке.")

@dp.message(BotStates.waiting_for_qualities_nick)
async def process_qualities(message: Message, state: FSMContext):
    user_nick = get_current_username(message)
    target = message.text.strip()
    if not target.startswith("@"):
        await message.answer("Неверный формат. Отправьте аккаунт вида @nickname.")
        return
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    loading = await message.answer("🔮 Тусую колоду 🔮")
    try:
        report = process_user_nicknames(user_nick, target[1:], qualities_prompt_)
        await loading.edit_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(e)
        await loading.edit_text("Карты Таро не знают ничего об этом человеке.")

@dp.message()
async def fallback(message: Message):
    await message.answer("Пожалуйста, используйте кнопки меню.")

async def main():
    global bot
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN не найден')
        return
    bot = Bot(token=BOT_TOKEN)
    logger.info(f'Бот запущен на {bot.id}')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
