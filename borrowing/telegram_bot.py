import os
import requests
from dotenv import load_dotenv

load_dotenv()


def send_telegram_message(message: str) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print(
            f"[Telegram Bot Error]: Missing credentials! TOKEN={bool(bot_token)}, CHAT_ID={bool(chat_id)}"
        )
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print("[Telegram Bot]: Message sent successfully!")
    except requests.RequestException as error:
        print(f"[Telegram Bot Error]: {error}")
        if getattr(error, "response", None) is not None:
            print(f"[Telegram Response]: {error.response.text}")
