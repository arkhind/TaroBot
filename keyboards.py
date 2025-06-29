from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔮 Ответы на вопросы", callback_data="answers"),
            InlineKeyboardButton(text="✅/❌ Да/нет", callback_data="yes_no"),
        ],
        [
            InlineKeyboardButton(
                text="🌅 Предсказание на день", callback_data="prediction"
            )
        ],
        [
            InlineKeyboardButton(
                text="💑 Совместимость", callback_data="compatibility"
            ),
            InlineKeyboardButton(
                text="⚖️ Плохие/хорошие качества", callback_data="qualities"
            ),
        ],
    ]
)


def get_zodiac_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора знака зодиака"""
    zodiac_signs = [
        ("♈ Овен", "zodiac_aries"),
        ("♉ Телец", "zodiac_taurus"),
        ("♊ Близнецы", "zodiac_gemini"),
        ("♋ Рак", "zodiac_cancer"),
        ("♌ Лев", "zodiac_leo"),
        ("♍ Дева", "zodiac_virgo"),
        ("♎ Весы", "zodiac_libra"),
        ("♏ Скорпион", "zodiac_scorpio"),
        ("♐ Стрелец", "zodiac_sagittarius"),
        ("♑ Козерог", "zodiac_capricorn"),
        ("♒ Водолей", "zodiac_aquarius"),
        ("♓ Рыбы", "zodiac_pisces"),
    ]
    
    # Создаем клавиатуру 3x4 (3 кнопки в ряду, 4 ряда)
    keyboard = []
    for i in range(0, len(zodiac_signs), 3):
        row = []
        for j in range(3):
            if i + j < len(zodiac_signs):
                text, callback_data = zodiac_signs[i + j]
                row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_name_keyboard(username: str, full_name: Optional[str] = None) -> InlineKeyboardMarkup:
    keyboard = []

    # Первая строка: никнейм
    if username and full_name and full_name != username:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"@{username}", callback_data=f"name_{username}"
                ),
                InlineKeyboardButton(text=full_name, callback_data=f"name_{full_name}"),
            ]
        )
    else:
        if username:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"@{username}", callback_data=f"name_{username}"
                    )
                ]
            )
        # Вторая строка: полное имя (если есть)
        elif full_name and full_name != username:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=full_name, callback_data=f"name_{full_name}"
                    )
                ]
            )

    # Третья строка: пропустить
    keyboard.append(
        [InlineKeyboardButton(text="Пропустить", callback_data="name_skip")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
