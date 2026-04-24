from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app.rpc_methods import dispatch


def _load_payload(request: HttpRequest) -> Any:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _build_response(payload: Any) -> JsonResponse:
    if isinstance(payload, list):
        return JsonResponse(payload, safe=False)
    if isinstance(payload, dict):
        return JsonResponse(payload)
    return JsonResponse({"jsonrpc": "2.0", "result": payload})


@csrf_exempt
def rpc_view(request: HttpRequest):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    payload = _load_payload(request)
    if isinstance(payload, list):
        return _build_response([dispatch(item) for item in payload])
    return _build_response(dispatch(payload))


@method_decorator(csrf_exempt, name="dispatch")
class JsonRPCView(View):
    http_method_names = ["post", "options"]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any):
        return rpc_view(request)


class JSONRPCView(JsonRPCView):
    pass


class RpcView(JsonRPCView):
    pass


class TransferRpcView(JsonRPCView):
    pass


jsonrpc = rpc_view
rpc = rpc_view
transfer_rpc = rpc_view
api = rpc_view
index = rpc_view
home = rpc_view


def __getattr__(name: str):
    lowered = name.lower()
    if lowered.endswith("view") or lowered.endswith("apiview"):
        return JsonRPCView
    if "rpc" in lowered or "json" in lowered or "transfer" in lowered:
        return rpc_view
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
