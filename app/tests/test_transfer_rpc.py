import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from app.models import Error, Transfer, TransferState


class DummyCardAdapter:
    def __init__(self, balance=Decimal("500000.00"), phone="+998901234567", active=True):
        self._balance = Decimal(balance)
        self._phone = phone
        self._active = active

    @property
    def balance(self):
        return self._balance

    @property
    def phone(self):
        return self._phone

    def is_active(self):
        return self._active

    def expiry_matches(self, expiry):
        return expiry == "12/26"

    def apply_balance_delta(self, delta):
        self._balance += Decimal(delta)

    def save(self):
        return None


class TransferRpcTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/api/json-rpc/"
        self._seed_errors()

    def _seed_errors(self):
        codes = {
            32701: "Ext id already exists",
            32702: "Balance is not enough",
            32703: "SMS service is not bind",
            32704: "Card expiry is not valid",
            32705: "Card is not active",
            32706: "Unknown error occurred",
            32707: "Currency not allowed except 860, 643, 840",
            32709: "Amount is small",
            32710: "OTP expired",
            32711: "Count of try is reached",
            32712: "OTP is wrong, left try count is 2",
            32713: "Method is not allowed",
        }
        for code, message in codes.items():
            Error.objects.get_or_create(code=code, defaults={"en": message, "ru": message, "uz": message})

    def rpc_call(self, payload):
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        return response, json.loads(response.content.decode("utf-8"))

    @patch("app.services.transfers.validate_card", return_value=True)
    @patch("app.services.transfers.generate_otp", return_value="123456")
    @patch("app.services.transfers.send_telegram_message", return_value=True)
    @patch("app.services.transfers.get_card_adapter")
    def test_transfer_create_returns_created_state(
        self,
        mocked_get_card_adapter,
        mocked_send,
        mocked_generate,
        mocked_validate_card,
    ):
        mocked_get_card_adapter.side_effect = [DummyCardAdapter(), DummyCardAdapter()]

        response, data = self.rpc_call(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "transfer.create",
                "params": {
                    "ext_id": "tr-create-1",
                    "sender_card_number": "4242424242424242",
                    "sender_card_expiry": "12/26",
                    "receiver_card_number": "5555555555554444",
                    "sending_amount": 15000,
                    "currency": 643,
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["result"]["state"], TransferState.CREATED)
        self.assertTrue(data["result"]["otp_sent"])
        self.assertTrue(Transfer.objects.filter(ext_id="tr-create-1").exists())
        mocked_send.assert_called_once()
        mocked_generate.assert_called_once()
        mocked_validate_card.assert_called()

    @patch("app.services.transfers.get_card_adapter")
    def test_transfer_confirm_wrong_otp_increments_try_count(self, mocked_get_card_adapter):
        mocked_get_card_adapter.side_effect = [DummyCardAdapter(), DummyCardAdapter()]
        transfer = Transfer.objects.create(
            ext_id="tr-confirm-1",
            sender_card_number="4242424242424242",
            receiver_card_number="5555555555554444",
            sender_card_expiry="12/26",
            sender_phone="+998901234567",
            sending_amount=Decimal("15000.00"),
            currency=643,
            receiving_amount=Decimal("2250000.00"),
            otp="123456",
        )

        response, data = self.rpc_call(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "transfer.confirm",
                "params": {"ext_id": transfer.ext_id, "otp": "000000"},
            }
        )

        transfer.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["error"]["code"], 32712)
        self.assertEqual(transfer.try_count, 1)
        self.assertEqual(transfer.state, TransferState.CREATED)

    def test_transfer_history_filters_by_status_and_date(self):
        first = Transfer.objects.create(
            ext_id="tr-history-1",
            sender_card_number="4242424242424242",
            receiver_card_number="5555555555554444",
            sender_card_expiry="12/26",
            sending_amount=Decimal("1000.00"),
            currency=643,
            receiving_amount=Decimal("150000.00"),
            state=TransferState.CONFIRMED,
            otp="111111",
        )
        second = Transfer.objects.create(
            ext_id="tr-history-2",
            sender_card_number="4242424242424242",
            receiver_card_number="5555555555554444",
            sender_card_expiry="12/26",
            sending_amount=Decimal("2000.00"),
            currency=643,
            receiving_amount=Decimal("300000.00"),
            state=TransferState.CANCELLED,
            otp="222222",
        )
        yesterday = timezone.now() - timedelta(days=1)
        Transfer.objects.filter(pk=first.pk).update(created_at=yesterday)
        Transfer.objects.filter(pk=second.pk).update(created_at=timezone.now())

        response, data = self.rpc_call(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "transfer.history",
                "params": {
                    "card_number": "4242424242424242",
                    "start_date": timezone.now().date().isoformat(),
                    "end_date": timezone.now().date().isoformat(),
                    "status": "cancelled",
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["result"]), 1)
        self.assertEqual(data["result"][0]["ext_id"], second.ext_id)

    def test_populate_command_is_idempotent(self):
        Error.objects.all().delete()

        call_command("populatecommand")
        first_count = Error.objects.count()

        call_command("populatecommand")
        second_count = Error.objects.count()

        self.assertEqual(first_count, 15)
        self.assertEqual(second_count, 15)
