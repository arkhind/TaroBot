from aiogram import Dispatcher, types
from aiogram.filters import CallbackDataFilter
from loguru import logger

def register_answers_handlers(dp: Dispatcher):
    @dp.callback_query(CallbackDataFilter(data="yes_no"))
    async def handle_answers(callback: types.CallbackQuery):
        logger.info("User selected Yes_No")
        await callback.message.answer("Вы выбрали 'Да/нет'")
        await callback.answer()
