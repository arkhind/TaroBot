from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔮 Ответы на вопросы", callback_data="answers")],
    [InlineKeyboardButton(text="✅/❌ Да/нет", callback_data="yes_no")],
    [InlineKeyboardButton(text="💑 Совместимость", callback_data="compatibility")],
    [InlineKeyboardButton(text="🌅 Предсказание на день", callback_data="prediction")],
    [InlineKeyboardButton(text="⚖️ Плохие/хорошие качества", callback_data="qualities")]
])
