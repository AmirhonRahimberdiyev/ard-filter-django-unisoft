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
