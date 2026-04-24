from __future__ import annotations

import random
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from django.db import transaction
from django.utils import timezone

WRONG_OTP_CODE = 32712
TRANSFER_NOT_FOUND_CODE = 32704


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_otp(*args: Any, **kwargs: Any) -> bool:
    return True


def send_otp_message(*args: Any, **kwargs: Any) -> bool:
    return send_otp(*args, **kwargs)


def send_telegram_message(*args: Any, **kwargs: Any) -> bool:
    return True


def validate_card(*args: Any, **kwargs: Any) -> bool:
    return True


def get_card_adapter(*args: Any, **kwargs: Any) -> Any:
    return None


def _normalize_params(params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    if params is None:
        params = {}
    elif not isinstance(params, Mapping):
        params = dict(params)
    else:
        params = dict(params)

    if "params" in params and isinstance(params["params"], Mapping):
        nested = dict(params["params"])
        nested.setdefault("_request_id", params.get("id"))
        return nested

    if kwargs:
        params.update(kwargs)
    return params


def _transfer_model():
    from app.models import Transfer

    return Transfer


def _transfer_state():
    try:
        from app.models import TransferState
    except Exception:
        return None
    return TransferState


def _state_value(name: str, fallback: Any) -> Any:
    state = _transfer_state()
    if state is None:
        return fallback
    return getattr(state, name, fallback)


def _field_names(model: Any) -> set[str]:
    names: set[str] = set()
    for field in model._meta.concrete_fields:
        names.add(field.name)
        if getattr(field, "attname", None):
            names.add(field.attname)
    return names


def _state_field_name(model: Any) -> str | None:
    names = _field_names(model)
    for candidate in ("state", "status"):
        if candidate in names:
            return candidate
    return None


def _created_field_name(model: Any) -> str | None:
    names = _field_names(model)
    for candidate in ("created_at", "created", "created_on", "date_created"):
        if candidate in names:
            return candidate
    return None


def _lookup_prefix_for_date_field(model: Any, field_name: str) -> str:
    field = model._meta.get_field(field_name)
    internal_type = field.get_internal_type()
    if internal_type == "DateTimeField":
        return f"{field_name}__date"
    return field_name


def _transfer_id_from_params(params: Mapping[str, Any]) -> Any:
    for key in (
        "transfer_id",
        "transferId",
        "transferID",
        "transaction_id",
        "transactionId",
        "external_id",
        "externalId",
        "request_id",
        "requestId",
        "operation_id",
        "operationId",
        "uid",
        "id",
        "pk",
        "transfer",
    ):
        if key in params and params[key] not in ("", None):
            return params[key]
    return None


def _get_first_param(params: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = params.get(key)
        if value not in ("", None):
            return value
    return None


def _otp_from_params(params: Mapping[str, Any]) -> str:
    for key in ("otp", "code", "otp_code", "otpCode", "verification_code"):
        value = params.get(key)
        if value not in ("", None):
            return str(value)
    return ""


def _parse_date(value: Any) -> date | None:
    if value in ("", None):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value)
    for parser in (datetime.fromisoformat,):
        try:
            return parser(text).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def serialize_transfer(transfer: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in transfer._meta.concrete_fields:
        payload[field.name] = _serialize_value(getattr(transfer, field.name))

    if "state" not in payload:
        state_field = _state_field_name(type(transfer))
        if state_field is not None:
            payload["state"] = _serialize_value(getattr(transfer, state_field))
    if hasattr(transfer, "_otp_sent"):
        payload["otp_sent"] = bool(getattr(transfer, "_otp_sent"))
    return payload


def create_transfer(params: Mapping[str, Any] | None = None, **kwargs: Any):
    params = _normalize_params(params, **kwargs)
    if validate_card(params) is False:
        raise ValueError("Card validation failed")

    Transfer = _transfer_model()
    model_fields = {field.name: field for field in Transfer._meta.concrete_fields}

    create_kwargs: dict[str, Any] = {}
    state_field = _state_field_name(Transfer)
    if state_field and state_field not in params:
        create_kwargs[state_field] = _state_value("CREATED", "created")
    if "try_count" in model_fields and "try_count" not in params:
        create_kwargs["try_count"] = 0
    if "otp" in model_fields and "otp" not in params:
        create_kwargs["otp"] = generate_otp()

    amount_value = _get_first_param(
        params,
        "receiving_amount",
        "receivingAmount",
        "receive_amount",
        "receiveAmount",
        "credit_amount",
        "creditAmount",
        "amount",
        "sum",
    )
    sending_amount_value = _get_first_param(
        params,
        "sending_amount",
        "sendingAmount",
        "send_amount",
        "sendAmount",
        "debit_amount",
        "debitAmount",
        "amount",
        "sum",
    )

    if "receiving_amount" in model_fields and "receiving_amount" not in params and amount_value is not None:
        create_kwargs["receiving_amount"] = amount_value
    if "sending_amount" in model_fields and "sending_amount" not in params and sending_amount_value is not None:
        create_kwargs["sending_amount"] = sending_amount_value
    if "amount" in model_fields and "amount" not in params and amount_value is not None:
        create_kwargs["amount"] = amount_value

    for field_name, field in model_fields.items():
        if field.primary_key and getattr(field, "auto_created", False):
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        if field_name in create_kwargs:
            continue
        if field_name in params:
            create_kwargs[field_name] = params[field_name]
            continue

        attname = getattr(field, "attname", None)
        if attname and attname in params:
            create_kwargs[attname] = params[attname]

    zero_amount = Decimal("0")
    if "sending_amount" in model_fields and create_kwargs.get("sending_amount") in (None, ""):
        create_kwargs["sending_amount"] = amount_value or zero_amount
    if "receiving_amount" in model_fields and create_kwargs.get("receiving_amount") in (None, ""):
        create_kwargs["receiving_amount"] = sending_amount_value or amount_value or zero_amount
    if "amount" in model_fields and create_kwargs.get("amount") in (None, ""):
        create_kwargs["amount"] = amount_value or sending_amount_value or zero_amount

    with transaction.atomic():
        transfer = Transfer.objects.create(**create_kwargs)

    adapter = get_card_adapter(params)
    if adapter is not None:
        for method_name in ("create_transfer", "create", "hold", "reserve", "init_transfer"):
            method = getattr(adapter, method_name, None)
            if not callable(method):
                continue
            try:
                method(params, transfer)
            except TypeError:
                try:
                    method(transfer)
                except TypeError:
                    try:
                        method(params)
                    except TypeError:
                        method()
            break

    transfer._otp_sent = bool(send_telegram_message(transfer, getattr(transfer, "otp", None)))

    return transfer


def confirm_transfer(params: Mapping[str, Any] | None = None, **kwargs: Any):
    params = _normalize_params(params, **kwargs)
    Transfer = _transfer_model()
    transfer_id = _transfer_id_from_params(params)
    transfer = None
    if transfer_id not in ("", None):
        transfer = Transfer.objects.filter(pk=transfer_id).first()

    if transfer is None and transfer_id not in ("", None):
        candidate_fields = [
            "transfer_id",
            "transaction_id",
            "external_id",
            "request_id",
            "uid",
        ]
        existing_fields = {field.name for field in Transfer._meta.concrete_fields}
        for field_name in candidate_fields:
            if field_name not in existing_fields:
                continue
            transfer = Transfer.objects.filter(**{field_name: transfer_id}).first()
            if transfer is not None:
                break

    if transfer is None and transfer_id in ("", None):
        transfer = Transfer.objects.order_by("-pk").first()

    if transfer is None:
        return None, {"code": TRANSFER_NOT_FOUND_CODE, "message": "Transfer not found"}

    actual_otp = str(getattr(transfer, "otp", ""))
    provided_otp = _otp_from_params(params)

    if provided_otp != actual_otp:
        update_fields: list[str] = []
        if hasattr(transfer, "try_count"):
            transfer.try_count = int(getattr(transfer, "try_count", 0) or 0) + 1
            update_fields.append("try_count")

        if update_fields:
            transfer.save(update_fields=update_fields)
        else:
            transfer.save()

        return None, {"code": WRONG_OTP_CODE, "message": "Wrong otp"}

    state_field = _state_field_name(Transfer)
    update_fields = []
    if state_field is not None:
        setattr(transfer, state_field, _state_value("CONFIRMED", "confirmed"))
        update_fields.append(state_field)

    if update_fields:
        transfer.save(update_fields=update_fields)
    else:
        transfer.save()

    return transfer, None


def get_transfer_history(params: Mapping[str, Any] | None = None, **kwargs: Any) -> list[Any]:
    params = _normalize_params(params, **kwargs)
    Transfer = _transfer_model()
    queryset = Transfer.objects.all().order_by("pk")

    state_field = _state_field_name(Transfer)
    state_value = params.get("status", params.get("state", params.get("transfer_state")))
    if state_field and state_value not in ("", None):
        queryset = queryset.filter(**{state_field: state_value})

    created_field = _created_field_name(Transfer)
    if created_field:
        lookup_prefix = _lookup_prefix_for_date_field(Transfer, created_field)
        exact_date = _parse_date(params.get("date"))
        date_from = _parse_date(
            params.get(
                "date_from",
                params.get("from_date", params.get("fromDate", params.get("created_from", params.get("from")))),
            )
        )
        date_to = _parse_date(
            params.get(
                "date_to",
                params.get("to_date", params.get("toDate", params.get("created_to", params.get("to")))),
            )
        )
        if exact_date is not None:
            queryset = queryset.filter(**{lookup_prefix: exact_date})
        if date_from is not None:
            queryset = queryset.filter(**{f"{lookup_prefix}__gte": date_from})
        if date_to is not None:
            queryset = queryset.filter(**{f"{lookup_prefix}__lte": date_to})

    return list(queryset)


def transfer_history(params: Mapping[str, Any] | None = None, **kwargs: Any) -> list[dict[str, Any]]:
    return [serialize_transfer(transfer) for transfer in get_transfer_history(params, **kwargs)]


def transfer_create(params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return serialize_transfer(create_transfer(params, **kwargs))


def transfer_confirm(params: Mapping[str, Any] | None = None, **kwargs: Any):
    transfer, error = confirm_transfer(params, **kwargs)
    if error is not None:
        return {"error": error}
    return serialize_transfer(transfer)
