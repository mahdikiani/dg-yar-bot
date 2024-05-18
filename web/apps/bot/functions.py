from io import BytesIO
import logging
import os

from celery import shared_task
from tapsage import TapSageBot
from tapsage.tapsagebot import Session
from utils.texttools import telegram_markdown_formatter
import openai

from .Bot import TelegramBot

tapsage = TapSageBot(os.getenv("TAPSAGE_API_KEY"), os.getenv("TAPSAGE_BOT_ID"))
bot = TelegramBot()
logger = logging.getLogger("bot")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_session(user_id: str) -> Session:
    try:
        sessions = tapsage.list_sessions(user_id)
        logging.warning(f"Sessions: {user_id} {sessions}")
        if not sessions:
            session = tapsage.create_session(user_id)
        else:
            session = tapsage.retrieve_session(sessions[0].id)
            logging.info(f"\n{len(sessions)}\n{sessions[0]}\n{session}\n\n")
        return session
    except Exception as e:
        logging.error(e)
        return


@shared_task
def ai_response(
    message: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    **kwargs,
):
    session = get_session(user_id)
    stream = tapsage.stream_messages(session, message, split_criteria={"words": True})

    resp_text = ""
    new_piece = ""
    for msg in stream:
        new_piece += msg.message.content
        if new_piece[-1] == " " or len(new_piece) > 50:
            resp_text += new_piece
            if resp_text.count("`") % 2 == 0:
                bot.edit_message_text(
                    text=telegram_markdown_formatter(resp_text),
                    chat_id=chat_id,
                    message_id=response_id,
                    parse_mode="markdownV2",
                )
            new_piece = ""

    if resp_text and resp_text[-1] != " ":
        try:
            # logger.info(f"Final response: {resp_text}")
            bot.edit_message_text(
                text=telegram_markdown_formatter(resp_text),
                chat_id=chat_id,
                message_id=response_id,
                parse_mode="markdownV2",
            )
        except Exception as e:
            logger.error(f"Error:\n{e}\n{resp_text}")


@shared_task
def url_response(
    url: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    **kwargs,
):
    pass


def voice_response(voice_bytes: BytesIO, **kwargs):
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    return transcription.text


def send_voice_response(text: str, chat_id: str, **kwargs):
    response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    bot.send_voice(chat_id, buffer)
