from io import BytesIO
import logging
import os

from celery import shared_task
from tapsage import TapSageBot
from tapsage.tapsagebot import Session
from utils.texttools import telegram_markdown_formatter
from telebot.apihelper import ApiTelegramException
import openai

from .Bot import TelegramBot

tapsage = TapSageBot(os.getenv("TAPSAGE_API_KEY"), os.getenv("TAPSAGE_BOT_ID"))
bot = TelegramBot()
logger = logging.getLogger("bot")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_session(user_id: str) -> Session:
    try:
        sessions = tapsage.list_sessions(user_id)
        if not sessions:
            session = tapsage.create_session()
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
            try:
                if resp_text.count("`") % 2 == 0:
                    bot.edit_message_text(
                        text=telegram_markdown_formatter(resp_text),
                        chat_id=chat_id,
                        message_id=response_id,
                        parse_mode="markdownV2",
                    )
            except Exception as e:
                logger.error(f"Error editing message: {e} {resp_text}")
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
        except ApiTelegramException as e:
            if "message is not modified:" not in str(e):
                logger.error(f"Error:\n{e}\n{resp_text}")
        except Exception as e:
            logger.error(f"Error:\n{e}\n{resp_text}")


def voice_response(voice_bytes: BytesIO, **kwargs):
    logging.warning(f"voice received: {voice_bytes}")

    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    print(transcription)
    return transcription.text
