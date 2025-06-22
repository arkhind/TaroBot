from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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


def get_name_keyboard(username: str, full_name: str = None) -> InlineKeyboardMarkup:
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
