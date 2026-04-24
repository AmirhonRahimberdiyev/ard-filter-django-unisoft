import logging
from decimal import Decimal

from jsonrpcserver import Error as JsonRpcError
from jsonrpcserver import Success, method

from app.services.transfers import (
    TransferServiceError,
    cancel_transfer,
    confirm_transfer,
    create_transfer,
    get_transfer_history,
    get_transfer_state,
)

logger = logging.getLogger(__name__)


def serialize_amount(value):
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_transfer(transfer):
    payload = {
        "ext_id": transfer.ext_id,
        "sender_card_number": transfer.sender_card_number,
        "receiver_card_number": transfer.receiver_card_number,
        "sending_amount": serialize_amount(transfer.sending_amount),
        "receiving_amount": serialize_amount(transfer.receiving_amount),
        "currency": transfer.currency,
        "state": transfer.state,
        "try_count": transfer.try_count,
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
        "confirmed_at": transfer.confirmed_at.isoformat() if transfer.confirmed_at else None,
        "cancelled_at": transfer.cancelled_at.isoformat() if transfer.cancelled_at else None,
        "updated_at": transfer.updated_at.isoformat() if transfer.updated_at else None,
    }
    return payload


@method(name="transfer.create")
def transfer_create(
    ext_id,
    sender_card_number,
    receiver_card_number,
    sender_card_expiry,
    sending_amount,
    currency,
    sender_phone=None,
    receiver_phone=None,
):
    try:
        transfer = create_transfer(
            ext_id=ext_id,
            sender_card_number=sender_card_number,
            receiver_card_number=receiver_card_number,
            sender_card_expiry=sender_card_expiry,
            sending_amount=sending_amount,
            currency=currency,
            sender_phone=sender_phone,
            receiver_phone=receiver_phone,
        )
        return Success(
            {
                "ext_id": transfer.ext_id,
                "state": transfer.state,
                "otp_sent": True,
            }
        )
    except TransferServiceError as exc:
        logger.warning("transfer.create failed", extra={"ext_id": ext_id, "code": exc.code})
        return JsonRpcError(exc.code, exc.message)
    except Exception:
        logger.exception("transfer.create unexpected error", extra={"ext_id": ext_id})
        return JsonRpcError(32706, "Unknown error occurred")


@method(name="transfer.confirm")
def transfer_confirm(ext_id, otp):
    try:
        transfer = confirm_transfer(ext_id=ext_id, otp=otp)
        return Success({"ext_id": transfer.ext_id, "state": transfer.state})
    except TransferServiceError as exc:
        logger.warning("transfer.confirm failed", extra={"ext_id": ext_id, "code": exc.code})
        return JsonRpcError(exc.code, exc.message)
    except Exception:
        logger.exception("transfer.confirm unexpected error", extra={"ext_id": ext_id})
        return JsonRpcError(32706, "Unknown error occurred")


@method(name="transfer.cancel")
def transfer_cancel(ext_id):
    try:
        transfer = cancel_transfer(ext_id=ext_id)
        return Success({"ext_id": transfer.ext_id, "state": transfer.state})
    except TransferServiceError as exc:
        logger.warning("transfer.cancel failed", extra={"ext_id": ext_id, "code": exc.code})
        return JsonRpcError(exc.code, exc.message)
    except Exception:
        logger.exception("transfer.cancel unexpected error", extra={"ext_id": ext_id})
        return JsonRpcError(32706, "Unknown error occurred")


@method(name="transfer.state")
def transfer_state(ext_id):
    try:
        transfer = get_transfer_state(ext_id=ext_id)
        return Success({"ext_id": transfer.ext_id, "state": transfer.state})
    except TransferServiceError as exc:
        logger.warning("transfer.state failed", extra={"ext_id": ext_id, "code": exc.code})
        return JsonRpcError(exc.code, exc.message)
    except Exception:
        logger.exception("transfer.state unexpected error", extra={"ext_id": ext_id})
        return JsonRpcError(32706, "Unknown error occurred")


@method(name="transfer.history")
def transfer_history(card_number=None, start_date=None, end_date=None, status=None):
    try:
        transfers = get_transfer_history(
            card_number=card_number,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        result = []
        for transfer in transfers:
            data = serialize_transfer(transfer)
            result.append(
                {
                    "ext_id": data["ext_id"],
                    "sending_amount": data["sending_amount"],
                    "state": data["state"],
                    "created_at": data["created_at"],
                }
            )
        return Success(result)
    except TransferServiceError as exc:
        logger.warning("transfer.history failed", extra={"code": exc.code})
        return JsonRpcError(exc.code, exc.message)
    except Exception:
        logger.exception("transfer.history unexpected error")
        return JsonRpcError(32706, "Unknown error occurred")
