from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from apps.accounts.models import AIEngines, BotUser


def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        KeyboardButton("راهنما"),
        KeyboardButton("ناحیه کاربری"),
        KeyboardButton("خرید اعتبار"),
    )
    markup.add(
        KeyboardButton("مکالمه جدید"),
        KeyboardButton("نمایش مکالمه"),
        KeyboardButton("مکالمه‌ها"),
    )

    # markup.add(
    #     KeyboardButton("همگام سازی با سایر اکانت ها"),
    # )

    return markup


def select_ai_keyboard(user: BotUser, row_width=3):
    markup = InlineKeyboardMarkup(row_width=row_width)
    row = []
    for engine in AIEngines:
        if user.ai_engine == engine.name:
            row.append(
                InlineKeyboardButton(
                    f"✅ {engine.name}", callback_data=f"select_ai_{engine.name}"
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    engine.name, callback_data=f"select_ai_{engine.name}"
                )
            )

        if len(row) == row_width:
            markup.add(*row)
            row = []
    return markup


def read_keyboard(message_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("خواندن", callback_data=f"read_{message_id}"),
    )
    return markup


def answer_keyboard(message_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("جواب دادن", callback_data=f"answer_{message_id}"),
    )
    return markup
