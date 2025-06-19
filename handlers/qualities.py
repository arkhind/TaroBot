from aiogram import Dispatcher, types
from aiogram.filters import CallbackDataFilter
from loguru import logger

def register_answers_handlers(dp: Dispatcher):
    @dp.callback_query(CallbackDataFilter(data="quality"))
    async def handle_answers(callback: types.CallbackQuery):
        logger.info("User selected Quality")
        await callback.message.answer("Вы выбрали 'Плохие/хорошие качества'")
        await callback.answer()
