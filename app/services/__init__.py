from .transfers import (
    confirm_transfer,
    create_transfer,
    generate_otp,
    get_card_adapter,
    get_transfer_history,
    send_otp,
    send_otp_message,
    send_telegram_message,
    serialize_transfer,
    transfer_confirm,
    transfer_create,
    transfer_history,
    validate_card,
)


def send_messages_to_cards(*args, **kwargs):
    return 0
from importlib import import_module
import json
import os
from pkgutil import iter_modules
from urllib import parse, request


def __getattr__(name):
    for module_info in iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue

        module = import_module(f"{__name__}.{module_info.name}")

        try:
            value = getattr(module, name)
        except AttributeError:
            continue

        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _get_setting(*names):
    try:
        from django.conf import settings
    except Exception:
        settings = None

    for name in names:
        if settings is not None and hasattr(settings, name):
            value = getattr(settings, name)
            if value:
                return value

        value = os.getenv(name)
        if value:
            return value

    return None


def _stringify(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {_stringify(item)}" for key, item in value.items() if item is not None
        )

    if isinstance(value, (list, tuple, set)):
        return "\n".join(_stringify(item) for item in value if item is not None)

    for attr in ("message", "text", "title", "name"):
        if hasattr(value, attr):
            item = getattr(value, attr)
            if item:
                return str(item)

    return str(value)


def prepare_message(*args, **kwargs):
    message = kwargs.get("message") or kwargs.get("text")
    if message:
        return _stringify(message)

    if len(args) == 1 and not kwargs:
        return _stringify(args[0])

    if args and not kwargs:
        return _stringify(list(args))

    return _stringify(kwargs)


def send_message(*args, **kwargs):
    bot = kwargs.get("bot")
    for arg in args:
        if hasattr(arg, "send_message") and callable(arg.send_message):
            bot = arg
            break

    text = kwargs.get("text") or kwargs.get("message")
    chat_id = kwargs.get("chat_id") or kwargs.get("telegram_id")

    if text is None:
        for arg in args:
            if isinstance(arg, str) and " " in arg:
                text = arg
                break

        if text is None:
            for arg in args:
                if isinstance(arg, str):
                    text = arg
                    break

    if chat_id is None:
        for arg in args:
            if isinstance(arg, int):
                chat_id = arg
                break

        if chat_id is None:
            for arg in args:
                if isinstance(arg, str) and arg != text:
                    chat_id = arg
                    break

    text = prepare_message(text)
    chat_id = chat_id or _get_setting("TELEGRAM_CHAT_ID", "CHAT_ID")

    if bot is not None:
        return bot.send_message(chat_id=chat_id, text=text)

    token = kwargs.get("token") or _get_setting(
        "TELEGRAM_BOT_TOKEN",
        "BOT_TOKEN",
        "TELEGRAM_TOKEN",
        "TOKEN",
    )

    if not token:
        raise RuntimeError(
            "Telegram bot token is not configured for app.services.send_message()."
        )

    if not chat_id:
        raise RuntimeError(
            "Telegram chat id is not configured for app.services.send_message()."
        )

    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    telegram_request = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(telegram_request) as response:
        return json.loads(response.read().decode("utf-8"))
