import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
try:
    from jsonrpcserver import dispatch
except ModuleNotFoundError:
    def dispatch(*args, **kwargs):
        raise ModuleNotFoundError("jsonrpcserver is not installed")

try:
    from app import rpc_methods  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "jsonrpcserver":
        raise
    rpc_methods = None

ALLOWED_METHODS = {
    "transfer.create",
    "transfer.confirm",
    "transfer.cancel",
    "transfer.state",
    "transfer.history",
}


@csrf_exempt
def jsonrpc_endpoint(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": 32713, "message": "Method is not allowed"},
            },
            status=405,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": 32706, "message": "Unknown error occurred"},
            },
            status=400,
        )

    if payload.get("method") not in ALLOWED_METHODS:
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": 32714, "message": "Method not found"},
            },
            status=404,
        )

    response = dispatch(request.body.decode("utf-8"))
    if response is None:
        return HttpResponse(status=204)

    return HttpResponse(
        str(response),
        status=getattr(response, "http_status", 200),
        content_type="application/json",
    )
