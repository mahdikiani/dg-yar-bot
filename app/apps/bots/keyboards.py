from apps.accounts.schemas import Profile
from apps.ai.models import AIEngines
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from utils import b64tools


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


def select_ai_keyboard(profile: Profile, row_width=3):
    markup = InlineKeyboardMarkup(row_width=row_width)
    row = []
    for engine in AIEngines:
        if profile.data.ai_engine.name == engine.name:
            row.append(
                InlineKeyboardButton(
                    f"✅ {engine.name}",
                    callback_data=f"select_ai_{engine.name}",
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

    if len(row) > 0:
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
        InlineKeyboardButton(
            "جواب دادن", callback_data=f"answer_{message_id}"
        ),
    )
    return markup


def inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("رفتن به بات", url=f"https://t.me/tgyt_bot"),
    )
    return markup


def brief_keyboard(webpage_uid: str):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "پیشنهاد متن با هوش مصنوعی",
            callback_data=f"brief_textai_{webpage_uid}",
        ),
    )
    return markup


def content_keyboard(uid, select_state=(0, 0, 0, 0, 0)):
    content_titles = ["Title", "Subtitle", "Description", "CTA", "Image"]
    markup = InlineKeyboardMarkup(row_width=6)
    uid = b64tools.b64_encode_uuid_strip(uid)

    for i in range(5):
        krow = [
            InlineKeyboardButton(
                content_titles[i], callback_data=content_titles[i]
            ),
        ]
        for j in range(5):
            new_state = select_state[:i] + (j,) + select_state[i + 1 :]
            # new_state = "_".join(map(str, new_state))
            if select_state[i] == j:
                krow.append(
                    InlineKeyboardButton(
                        f"✅ {j+1}",
                        callback_data=f"content_select_{uid}_{new_state}",
                    ),
                )
            else:
                krow.append(
                    InlineKeyboardButton(
                        f"{j+1}",
                        callback_data=f"content_select_{uid}_{new_state}",
                    ),
                )
        markup.add(*krow)

    markup.add(
        InlineKeyboardButton(
            f"Generate", callback_data=f"content_submit_{uid}_{select_state}"
        )
    )
    return markup
